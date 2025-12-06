from functools import cached_property
import re
import uuid
from pydantic import BaseModel, Field, field_validator
from pydantic.fields import FieldInfo
from dataclasses import field, dataclass
from typing import Literal, Optional, Type, TYPE_CHECKING, Union
from pathlib import Path
import typing
import types
import json
from models.agent import AgentOutput, Replicator, Tool
if TYPE_CHECKING:
    from src.agent import Agent

@dataclass
class LlmInstructions:
    background: str
    steps: list[str]
    tools: list[Type[Tool]]
    reasoning: bool
    output_schema: Type[BaseModel]

    def __post_init__(self):
        self._reasoning_instructions: dict = {
            'step': 'Em primeiro lugar, você deve justificar as suas decisões no campo `__reasoning__`',
            'description': 'Aqui você deverá justificar brevemente os passos que influenciaram as suas decisões',
            'typing': 'str'
        }
        self._tools_instructions: dict = {
            'step': 'Você tem a capacidade de usar as `tools` caso precise fazer operações externas, elas serão descritas adiante.',
        }
        if self.reasoning:
            self.steps.insert(0, self._reasoning_instructions['step'])
        if self.tools:
            self.steps.insert(1, self._tools_instructions['step'])

    def _jdumps(self, obj: dict) -> str:
        return json.dumps(obj, indent=4, ensure_ascii=False)
    
    def _get_typing_subschemas(self, field_type: set[type]):
        subargs = (sum([list(typing.get_args(t)) for t in field_type], []))
        if not subargs: return field_type
        for s in subargs:
            if typing.get_args(s):
                subargs += self._get_typing_subschemas({s})
        return [s for s in subargs if isinstance(s, type) and issubclass(s, BaseModel)]
    
    def _get_subschemas(self, models: dict[Type[BaseModel], int]):
        subschemas = {}
        for model, depth in models.items():
            typing_subschemas = self._get_typing_subschemas({model})
            for schema in typing_subschemas:
                if isinstance(schema, type) and issubclass(schema, BaseModel):
                    subschemas |= ({schema: depth})
                for field in schema.model_fields.values():
                    if isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
                        subschemas |= ({field.annotation: depth})
                        subschemas |= (self._get_subschemas({field.annotation: depth+1}))
        return subschemas

    def _format_field_type(self, field_value: FieldInfo) -> str:
        if isinstance(field_value.annotation, type):
            field_type = field_value.annotation.__name__
        else:
            field_type = re.sub(r"\b[\w\d_]+\.", "", str(field_value.annotation))
        return field_type
    
    def _format_tool(self, tool: Type[Tool]) -> str:
        tool_schema = tool.model_json_schema()
        formatted = f'```Tool <{tool.__name__}>\n'  
        tool_dict = {
            'tool_description': tool_schema['description'],
            'args_description': {},
            'tool_call_format': {tool.__name__: {}}
        }

        for field_name, field_value in tool.model_fields.items():
            tool_dict['tool_call_format'][tool.__name__][field_name] = self._format_field_type(field_value)
            tool_dict['args_description'][field_name] = field_value.description

        formatted += self._jdumps(tool_dict)
        return formatted + '\n```'

    def _format_schema(self) -> str:
        subschemas_list = []
        subschemas = list(self._get_subschemas({
            f.annotation: 0 for f in self.output_schema.model_fields.values() 
            if f.annotation is not None
        }))[::-1]
        
        for subschema in subschemas:
            subschema_dict = {}
            for subschema_field_name, subschema_field_value in subschema.model_fields.items():
                subschema_dict[subschema_field_name] = self._format_field_type(subschema_field_value)
            subschemas_list.append(
                f'```subschema <{subschema.__name__}>\n' + self._jdumps(subschema_dict) + '\n```'
            )
        schema_type = {} if not self.reasoning else {
            '__reasoning__': self._reasoning_instructions['typing']
        }
        schema_description = [] if not self.reasoning else [
            f' - __reasoning__: {self._reasoning_instructions["description"]}'
        ]
        for field_name, field_value in self.output_schema.model_fields.items():
            schema_type[field_name] = self._format_field_type(field_value)
            schema_description.append(f' - {field_name}: {field_value.description}')
        
        formatted = '* subschemas utilizados:\n' + '\n'.join(subschemas_list) + '\n\n'
        formatted += f'* descrição do output schema:\n' + '\n'.join(schema_description) + '\n\n' 
        formatted +=  f'* Output schema:\n' 
        return formatted + self._jdumps(schema_type)
    

    @property
    def content(self):
        formatted = self.background + '\n'

        for i, step in enumerate(self.steps):
            formatted += f" - ({i+1}) {step}\n"
        formatted += '\n'
        tools = []
        for tool in self.tools:
            tools.append(self._format_tool(tool))
        tools_formatted ='\n\n'.join(tools)

        schema_formatted = self._format_schema()
        formatted += f'[Tools]:\n{tools_formatted}'
        formatted += f'\n\n[Schema de resposta]:\n{schema_formatted}'
        return formatted

class UltraBasicTime(BaseModel):
    day2: int

class SuperBasicTime(BaseModel):
    day: int
    ultra_basic_time: UltraBasicTime

class CompleteTime(BaseModel):
    second: int
    minute: int
    hour: int
    basic_time: 'BasicTime'

class BasicTime(BaseModel):
    super_basic_time: SuperBasicTime
    month: int
    year: int

class ClimateOutput(Replicator):
    city: str | None = Field(
        description="Cidade onde será feita a pesquisa do clima"
    )
    time: Optional[list[list[CompleteTime | Optional[BasicTime]]]] = Field(
        description="Data do clima, é um objeto que pode ser nulo"
    )
    # tools: Optional[list[Tool]] = Field(
    #     description='Ferramentas que serão utilizadas para a tarefa, escreva o nome da ferramenta e os argumentos delas'
    # )


class InternalClimateTool(Tool):
    """Retorna o clima atual de algum cômodo da casa"""
    room: str = Field(
        description='Local da casa'
    )

    def tool(self) -> str:
        return '25°C'
    
class ExternalClimateTool(Tool):
    """Retorna o clima de uma cidade em uma data específica"""
    city: str | None = Field(
        description="Cidade onde será feita a pesquisa do clima"
    )

    def tool(self) -> str:
        return '20°C'


import os
os.system('cls')

inst = LlmInstructions(
    background='Você é um assistente de automação residencial focado em informações sobre o clima. Seu objetivo é interpretar comandos do usuário e classificar a ação necessária de acordo com os cômodos e parâmetros disponíveis. Sempre responda no formato JSON.',
    steps=[
        'Leia atentamente a pergunta do usuário e identifique seu tema central.',
        'Analise se a pergunta está relacionada a algum dos tópicos disponíveis nas tags.',
    ],
    tools=[InternalClimateTool, ExternalClimateTool],
    reasoning=True,
    output_schema=ClimateOutput,
)

print(inst.content)

# [print(i) for i in inst._get_typing_sub_args(ClimateOutput.model_fields['time'].annotation)]



# print(json.dumps(ClimateOutput.model_json_schema(), indent=4, ensure_ascii=False))
# print(ToolPromptFormatter([ClimateOutput]).format())

# print(get_origin(Optional[str | ClimateOutput]), get_args(Optional[str | ClimateOutput]))

# for t in get_args(Optional[str | ClimateOutput]):
    # print(issubclass(t, BaseModel))

# print(get_origin(str | None), get_args(str | None))
# print(get_origin(str | ClimateOutput), get_args(str | ClimateOutput))
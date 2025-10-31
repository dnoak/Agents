from functools import cached_property
import re
import uuid
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from dataclasses import dataclass
from typing import Literal, Optional, Type
import typing
import json
from models.agent import Tool, ToolTask, AgentOutputInjector

@dataclass
class LlmInstructions:
    background: str
    steps: list[str]
    tools: list[Type[Tool]]
    reasoning: bool
    output_schema: Type[BaseModel]

    def __post_init__(self):
        self._tools_steps: list = [
            'Responda somente com chamadas de funções e seus argumentos **seguindo a tipagem correta** das [Tools].',
            'Você vai funcionar em um loop onde em cada iteração você pode montar uma query de [Tools], e o resultado será reenviado para você.',
            'Não repita queries já feitas, aproveite o resultado delas para usar como entrada para a próxima query.',
            'Em uma mesma query, o resultado de uma função pode ser passado como argumento para outra. Exemplo: "ToolA(1, ToolB(ToolC("a", "b"), 3))."',
            'Use exclusivamente a estrutura/sintaxe de chamadas de função, não use elementos extras nessas chamadas.',     
            'O loop continuará até que todas as operações necessárias sejam concluídas.',
            'Você não deve tentar prever resultados de uma [Tool], sempre use elas para gerar os resultados.',
            'Quando o resultado final for concluído, você deve marcar o campo `_task_completion_status` de acordo com o status da tarefa.'
        ]
        self._typing_to_json: dict[str, str] = {
            'None': 'null',
        }
        self.tab = ' '*4
        if self.reasoning:
            self.steps.insert(0, 'Em primeiro lugar, você deve justificar as suas decisões no campo `_reasoning`')
        self.steps.append('**SEMPRE RESPONDA EM FORMATO JSON VÁLIDO**.') 

        self.output_schema = AgentOutputInjector(
            reasoning=self.reasoning,
            tool=len(self.tools) > 0
        ).inject(output_schema=self.output_schema)

        if self.tools:
            self.validated_tools = {
                t.__name__: t for t in self.tools
            }

    def _jdumps(self, obj: dict) -> str:
        return json.dumps(obj, indent=4, ensure_ascii=False)
    
    def _format_field_type(self, field_value: FieldInfo | type) -> str:
        if isinstance(field_value, type):
            return field_value.__name__
        if isinstance(field_value.annotation, type):
            return field_value.annotation.__name__
        formatted = re.sub(r"\b[\w\d_]+\.", "", str(field_value.annotation))
        for python_type, json_type in self._typing_to_json.items():
            formatted = formatted.replace(python_type, json_type)
        return formatted
    
    def _tool_return_type(self, tool: type[Tool]) -> str:
        return_annotation = typing.get_type_hints(getattr(tool, 'tool'))['return']
        return self._format_field_type(return_annotation)

    def _tool_gen_def_line(self, tool: type[Tool]) -> str:
        def_line = f'def {tool.__name__}('
        args = []
        args_description = []
        for field_name, field_value in tool.model_fields.items():
            args += [f'{field_name}: {self._format_field_type(field_value)}']
            args_description += [f'{field_name}: {field_value.description}']
        def_line += f"{', '.join(args)}) -> {self._tool_return_type(tool)}:\n"
        return def_line
    
    def _tool_gen_args_docstring(self, tool: type[Tool]) -> str:
        args = ''
        for field_name, field_value in tool.model_fields.items():
            args += f'{self.tab*2}{field_name}: {self._format_field_type(field_value)}\n'
            args+= f'{self.tab*3}{field_value.description}\n'
        return args
        
    def _tool_generate(self, tool: type[Tool]) -> str:
        def_line = self._tool_gen_def_line(tool)
        assert tool.__doc__ is not None, f'tool {tool.__name__} has no documentation'
        docs = tool.__doc__.strip().split('\n')
        docstring = f'{self.tab}"""' + str(*[f'\n    {l}' for l in docs]) + '\n'
        args_docstring = f'{self.tab}[Parameters]\n' + self._tool_gen_args_docstring(tool)
        # return_docstring = f'{self.tab}[Return]\n' + f'{self.tab*2}{self._return_type()}\n'
        return def_line + docstring + args_docstring + f'{self.tab}"""'
    
    def _get_typing_subschemas(self, field_type: set[type]):
        subargs = (sum([list(typing.get_args(t)) for t in field_type], []))
        if not subargs: return field_type
        for s in subargs:
            if typing.get_args(s):
                subargs += self._get_typing_subschemas({s})
        return [s for s in subargs if isinstance(s, type) and issubclass(s, BaseModel)]
    
    def _get_subschemas(self, models: dict[type[BaseModel], int]) -> dict[Type[BaseModel], int]:
        subschemas = {}
        for model, depth in models.items():
            typing_subschemas = self._get_typing_subschemas({model})
            for schema in typing_subschemas:
                if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
                    continue
                subschemas |= ({schema: depth})
                for field in schema.model_fields.values():
                    if isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
                        subschemas |= ({field.annotation: depth})
                        subschemas |= (self._get_subschemas({field.annotation: depth+1}))
        return subschemas

    def _format_schema(self) -> str:
        subschemas_list: list[str] = []
        subschemas = list(self._get_subschemas({
            f.annotation: 0 for f in self.output_schema.model_fields.values() 
            if f.annotation is not None
        }))[::-1]

        for subschema in subschemas:
            subschema_dict = {}
            for subschema_field_name, subschema_field_value in subschema.model_fields.items():
                subschema_dict[subschema_field_name] = self._format_field_type(subschema_field_value)
            subschemas_str = f'```subschema <{subschema.__name__}>\n' + self._jdumps(subschema_dict) + '\n```'
            subschemas_list.append(subschemas_str)
        schema_type = {}
        schema_description = []
        for field_name, field_value in self.output_schema.model_fields.items():
            if field_value.alias is not None:
                field_name = field_value.alias
            schema_type[field_name] = self._format_field_type(field_value)
            schema_description.append(f'{self.tab}→ {field_name}: {field_value.description}')
        formatted = ''
        if subschemas:
            formatted = '* subschemas utilizados:\n' + '\n'.join(subschemas_list) + '\n\n'
        formatted += f'[descrição do Output Schema]:\n' + '\n'.join(schema_description) + '\n\n' 
        #formatted +=  f'[Output Schema]:\n' 
        return formatted # + self._jdumps(schema_type)
    
    @property
    def content(self):
        formatted = self.background + '\n'

        for i, step in enumerate(self.steps):
            formatted += f" - ({i+1}) {step}\n"

        tools = []
        if self.tools:
            formatted += '\n[Tools steps]:\n'
            for i, step in enumerate(self._tools_steps):
                formatted += f" - ({i+1}) {step}\n"
            for tool in self.tools:
                tools.append(self._tool_generate(tool))
            tools_formatted ='\n\n'.join(tools)
            formatted += f'\n[Tools]:\n{tools_formatted}'
        formatted += f'\n\n[Schema de resposta]:\n{self._format_schema()}'
        return formatted

if __name__ == '__main__':
    import os
    from models.agent import Classifier, Replicator

    class UltraBasicTime(BaseModel):
        day2: int

    class SuperBasicTime(BaseModel):
        day: int
        ultra_basic_time: UltraBasicTime
    
    class CompleteTime(BaseModel):
        second: int | None
        minute: int
        hour: int
        basic_time: 'BasicTime'

    class BasicTime(BaseModel):
        super_basic_time: SuperBasicTime
        month: int
        year: int

    class ClimateOutput(Replicator):
        city: str = Field(
            description="Cidade onde será feita a pesquisa do clima"
        )
        time: Optional[list[list[CompleteTime]]] = Field(
            description="Data do clima, é um objeto que pode ser nulo"
        )
        # ok: bool = Field(
        #     description="Se a pesquisa foi bem sucedida"
        # )
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
        internal: InternalClimateTool = Field(
            description='Ferramenta que será utilizada para a tarefa'
        )

        def tool(self) -> str:
            return '20°C'


    import os
    from rich import print
    os.system('cls')

    inst = LlmInstructions(
        background='Você é um assistente de automação residencial focado em informações sobre o clima. Seu objetivo é interpretar comandos do usuário e classificar a ação necessária de acordo com os cômodos e parâmetros disponíveis. Sempre responda no formato JSON.',
        steps=[
            'Leia atentamente a pergunta do usuário e identifique seu tema central.',
            'Analise se a pergunta está relacionada a algum dos tópicos disponíveis nas tags.',
        ],
        tools=[],#[InternalClimateTool, ExternalClimateTool],
        reasoning=True,
        output_schema=ClimateOutput,
    )

    print(inst.content)
    print(ClimateOutput.model_json_schema())
        
    # print(LlmInstructions([ExternalClimateTool, InternalClimateTool]).content)
    # print([t for t in inst.validated_tools.values()])
    # print(inst.validated_tools['InternalClimateTool']())
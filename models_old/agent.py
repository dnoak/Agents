import inspect
import re
from typing_extensions import Unpack
from pydantic import BaseModel, ConfigDict, Field
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Optional

import pydantic
from src.message import Messages
if TYPE_CHECKING:
    from src.agent import Agent

class Processor(ABC):
    @abstractmethod
    def process(
        self, agent: 'Agent', 
        messages: list[Messages], 
        llm: dict
    ) -> dict | None:
        ...

class AgentOutput(ABC, BaseModel):
    model_config = ConfigDict(extra='allow') # *********************** ANALISAR CONSEQUÊNCIAS

    @classmethod
    def annotations(cls):
        only_type = lambda d: re.sub(r"<class '([\w]+)'>", r"\1", str(d))
        remove_typing_module = lambda d: d.replace('typing.', '')
        stringfy = lambda d: {
            k: stringfy(v)
            if isinstance(v, dict)
            else remove_typing_module(only_type(v))
            for k, v in d.items()
        }
        return stringfy(cls.__annotations__)

    @classmethod
    @abstractmethod
    def connection_type(cls) -> str: ...
    
    @classmethod
    @abstractmethod
    def node_attributes(cls) -> dict: ...

    @classmethod
    def node_label(
            cls, agent: 'Agent', running: bool = False,
            outputs_label: Literal['vertical', 'horizontal'] = 'vertical'
        ) -> str:
        node_color = '#228B22' if running else 'royalblue'
        outputs = [
            f'<TD PORT="here" BGCOLOR="#444444"><FONT POINT-SIZE="12.0" COLOR="white">{k}: {v}</FONT></TD>' 
            for k, v in agent.output_schema.annotations().items()
        ]
        if outputs_label == 'vertical':
            colspan = 1
            outputs = "".join([f"<TR>{output}</TR>" for output in outputs])
        elif outputs_label == 'horizontal':
            colspan = len(outputs)
            outputs = '<TR>' + ''.join(outputs) + '</TR>'
        return f'''
        <<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
            <TR>
                <TD COLSPAN="{colspan}" BGCOLOR="{node_color}"><FONT POINT-SIZE="20.0" COLOR="white">{agent.name}</FONT></TD>
            </TR>
            {outputs}
        </TABLE>>'''.strip()

    @classmethod
    @abstractmethod
    def edge_attributes(cls, running: bool = False) -> dict: ...

class Replicator(AgentOutput):
    @classmethod
    def connection_type(cls) -> str:
        return '__replicator__'
    
    @classmethod
    def node_attributes(cls) -> dict:
        return {
            'shape': 'plaintext',
            'color': '#e6e6e6'  
        }
    
    @classmethod
    def edge_attributes(cls, running: bool = False) -> dict:
        return {
            'style': 'bold',
            'color': 'green' if running else '#e6e6e6',
            'fontcolor': 'green' if running else '#e6e6e6',
        }

class Classifier(AgentOutput):
    @classmethod
    def connection_type(cls) -> str:
        return '__classifier__'
    
    @classmethod
    def node_attributes(cls) -> dict:
        return {
            'shape': 'plaintext',
            'color': '#e6e6e6',
        }
    
    @classmethod
    def edge_attributes(cls, running: bool = False) -> dict:
        return {
            'style': 'bold',
            'arrowhead': 'odot',
            'style': 'bold',
            'color': 'green' if running else '#e6e6e6',
            'fontcolor': 'green' if running else '#e6e6e6',
        }

class Tool(ABC, BaseModel):
    model_config = ConfigDict(extra='forbid')

    # @classmethod
    # def __shared__(cls):
    #     # print(cls.__class__.__dict__.keys())
    #     module_classes = dict(inspect.getmembers(inspect.getmodule(cls.__dict__)))
    #     print(module_classes.keys())
    #     assert '__shared__' in module_classes, \
    #         f'`__shared__` class must be defined in the same module as {cls.__class__.__dict__.__name__}'
    #     return module_classes['__shared__']().model_dump()

    # def __init__(self, *args, **kwargs):
    #     ...
        # super().__init__(*args, **kwargs)
        # module_classes = dict(inspect.getmembers(inspect.getmodule(self.__class__)))
        # assert '__shared__' in module_classes, \
        #     f'`__shared__` class must be defined in the same module as {self.__class__.__name__}'
        # self.__shared__ = module_classes['__shared__']().model_dump()
    
    @abstractmethod
    def tool(self) -> str: ...

class ToolTask(BaseModel):
    status: Literal['pending', 'success', 'failed'] = Field(
        description='Status da tarefa: Pending = pendente; success = concluída com sucesso; failed = concluída com falha.',
    )
    steps: list[str] = Field(
        description='Passo a passo das tarefas que faltam para concluir a tarefa.',
    )
    tools_query: str = Field(
        description='Query usando as [Tools]. Você pode usar o resultado de uma query como input de outra.',	 
    )

class ToolSchema(BaseModel):
    task_completion_status: Literal['pending', 'success', 'failed'] = Field(
        description='Status da tarefa: `pending` = pendente; `success` = concluída com sucesso; `failed` = concluída com falha.',
        alias='_task_completion_status',
    )
    task_remaining_steps: list[str] = Field(
        description='Passo a passo descrevendo textualmente o que falta para concluir a tarefa. A cada nova iteração uma etapa será removida',  
        alias='_task_remaining_steps',
    )
    tool_query: str | None = Field(
        description='Query usando as [Tools]. Você pode usar o resultado de uma query como input de outra.',
        alias='_tool_query',
    )

class ReasoningSchema(BaseModel):
    reasoning: str = Field(
        description='Justifique brevemente os passos que influenciaram as suas decisões.',
        alias='_reasoning',
    )

@dataclass
class AgentOutputInjector:
    reasoning: bool
    tool: bool

    def inject(self, output_schema: type[BaseModel]) -> type[AgentOutput]: 
        if self.tool:
            output_schema = type(output_schema.__name__, (output_schema, ToolSchema), {})
        if self.reasoning:
            output_schema = type(output_schema.__name__, (output_schema, ReasoningSchema), {})
        return output_schema

if __name__ == '__main__':
    import json
    class Time(BaseModel):
        second: int
        minute: int
        hour: int

    injected = AgentOutputInjector(reasoning=False, tool=True).inject(output_schema=Time)
    # object = {
    #     '__tool_status__': 'success',
    #     '__tool_steps__': ['passo 1', 'passo 2'],
    #     '__tool_query__': 'query',
    #     'hour': 12,
    #     'minute': 30,        
    #     'second': 0,
    # }

    print(json.dumps(injected.model_json_schema(), indent=4, ensure_ascii=False))

    # print(json.dumps(injected(**object).model_dump(by_alias=True), indent=4, ensure_ascii=False))

    # for k, v in injected.model_fields.items():
    #     print(f'{k}: {v.alias}')
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pydantic import BaseModel
from typing import Any, ClassVar, Literal, Protocol, TYPE_CHECKING
import inspect
import re
from typing_extensions import Unpack
from pydantic import BaseModel, ConfigDict, Field
from abc import ABC, abstractmethod
from dataclasses import dataclass
# if TYPE_CHECKING:
#     from src.node import Node

class NodeAttributes:
    @property
    def digraph_graph(self) -> dict:
        return {
            'size': '500,500',
            'bgcolor': '#353B41',
        }
    
    @property
    def digraph_node(cls) -> dict:
        return {
            'shape': 'plaintext',
            'color': '#e6e6e6'  
        }
    
    def node_label(
            self,
            name: str, 
            output_schema: Any,
            running: bool = False,
        ) -> str:
        node_color = '#228B22' if running else 'royalblue'
        return f'''
        <<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
            <TR>
                <TD COLSPAN="1" BGCOLOR="{node_color}">
                    <FONT POINT-SIZE="20.0" COLOR="white">{name}</FONT>
                </TD>
            </TR>
            <TR>
                <TD PORT="here" BGCOLOR="#444444">
                    <FONT POINT-SIZE="12.0" COLOR="white">{output_schema.__name__}</FONT>
                </TD>
            </TR>
        </TABLE>>'''.strip()

    def edge(self, running: bool = False) -> dict:
        return {
            'style': 'bold',
            'color': 'green' if running else '#e6e6e6',
            'fontcolor': 'green' if running else '#e6e6e6',
        }

@dataclass
class NodeOutput:
    execution_id: str
    source: Node | None
    result: Any


class NodeProcessor(ABC, BaseModel):
    node: Node = Field(init=False)
    inputs: dict[str, NodeOutput] = Field(init=False)
    routing: list[Node] = Field(init=False)
    
    @abstractmethod
    async def execute(self) -> Any:
        ...

class NodeProcessorBase(BaseModel):
    node: Node
    inputs: dict[str, NodeOutput]
    routing: list[Node]
    model_config = ConfigDict(extra='allow')

    async def execute(self) -> Any:
        raise NotImplementedError('Replace this method with your own logic')

@dataclass
class NodesExecutions:
    executions: dict[str, dict[str, NodeOutput]] = field(default_factory=dict)
    
    def insert(self, execution_id: str, node_output: NodeOutput):
        if execution_id not in self.executions:
            self.executions[execution_id] = {}
        source = '__input__' if node_output.source is None else node_output.source.name
        self.executions[execution_id][source] = node_output
    
    def get(self, execution_id: str) -> dict[str, NodeOutput]:
        return self.executions[execution_id]

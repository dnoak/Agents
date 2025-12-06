from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pydantic import BaseModel
from typing import Literal, Protocol, TYPE_CHECKING
import inspect
import re
from typing_extensions import Unpack
from pydantic import BaseModel, ConfigDict, Field
from abc import ABC, abstractmethod
from dataclasses import dataclass
if TYPE_CHECKING:
    from src.node import Node

class NodeRouting(Protocol):
    routes: list['Node']

class NodeReplicator(NodeRouting):
    routes: list['Node'] = field(default_factory=list)

@dataclass
class NodeOutput:
    execution_id: str
    source: 'Node | None'
    result: int
    routing: NodeRouting = field(default_factory=NodeReplicator)

@dataclass
class NodeProcessor(ABC):
    @abstractmethod
    async def process(self, prev_results: list[NodeOutput]) -> int:
        ...

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


class NodeOutputSchema(BaseModel):
    model_config = ConfigDict(extra='allow')

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
    def node_attributes(cls) -> dict:
        return {
            'shape': 'plaintext',
            'color': '#e6e6e6'  
        }
    
    @classmethod
    def node_label(
            cls,
            node: 'Node', 
            running: bool = False,
            outputs_label: Literal['vertical', 'horizontal'] = 'vertical'
        ) -> str:
        node_color = '#228B22' if running else 'royalblue'
        outputs = [
            f'<TD PORT="here" BGCOLOR="#444444"><FONT POINT-SIZE="12.0" COLOR="white">{k}: {v}</FONT></TD>' 
            for k, v in node.output_schema.annotations().items()
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
                <TD COLSPAN="{colspan}" BGCOLOR="{node_color}"><FONT POINT-SIZE="20.0" COLOR="white">{node.name}</FONT></TD>
            </TR>
            {outputs}
        </TABLE>>'''.strip()

    @classmethod
    def edge_attributes(cls, running: bool = False) -> dict:
        return {
            'style': 'bold',
            'color': 'green' if running else '#e6e6e6',
            'fontcolor': 'green' if running else '#e6e6e6',
        }
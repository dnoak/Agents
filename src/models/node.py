from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, Literal
from types import MethodType
from abc import ABC
from dataclasses import dataclass
from config import settings
if TYPE_CHECKING:
    from src.nodes.node import Node

@dataclass
class NodeSource:
    id: str
    node: 'Node | None'
    # routing: 'NodeRouting' = field(
    #     default_factory=lambda: NodeRouting(
    #         choices={},
    #         # default_policy='all',
    #         flags=NodeRoutingFlags(),
    #     )
    # )

@dataclass
class NodeOutputFlags:
    canceled: bool = False
    error: bool = False

@dataclass
class NodeOutput:
    execution_id: str
    source: NodeSource
    # routing: 'NodeRouting'
    result: Any
    flags: NodeOutputFlags

@dataclass
class NotProcessed:
    pass

_NotProcessed = NotProcessed()

@dataclass
class _NodeProcessor:
    node: 'Node'
    inputs: 'NodeInputs'
    routing: 'NodeRouting'
    
    def __post_init__(self):
        self.result: Any = _NotProcessed

    def inject_processor_fields(self, fields: set[str]) -> '_NodeProcessor':
        if self.node is None:
            return self
        for f in fields:
            setattr(self, f, getattr(self.node.processor, f))
        self.execute = MethodType(self.node.processor.execute.__func__, self)
        return self
    
    async def execute(self) -> Any:
        raise NotImplementedError('Replace this method with your own logic')

@dataclass
class NodeProcessor(ABC):
    node: 'Node' = field(init=False, repr=False)
    inputs: 'NodeInputs' = field(init=False, repr=False)
    routing: 'NodeRouting' = field(init=False, repr=False)

    @abstractmethod
    def execute(self) -> Any:
        ...

@dataclass
class NodeInputs:
    _node: 'Node'
    _inputs: list[NodeOutput]

    def __post_init__(self):
        self._dict_inputs = {
            i.source.node.name if i.source.node 
            else settings.node.first_execution_source:
            i for i in self._inputs
        }

    def __getitem__(self, node_name: str) -> NodeOutput:
        if node_name in self._dict_inputs:
            return self._dict_inputs[node_name]
        raise KeyError(
            f'Input `{node_name}` not found in {self._node.name}. Available inputs are {list(self._dict_inputs.keys())}'
        )

    def __iter__(self):
        return iter(self._dict_inputs.values())
    
    @property
    def results(self) -> list[Any]:
        return [
            i.result for i in self._dict_inputs.values()
            if i.flags.canceled is False
        ]

@dataclass
class NodesExecutions:
    executions: dict[str, dict[str, NodeOutput]] = field(default_factory=dict)
    
    def insert(self, node_output: NodeOutput):
        if node_output.execution_id not in self.executions:
            self.executions[node_output.execution_id] = {}
        if node_output.source.node is None:
            source_name = settings.node.first_execution_source
        else:
            source_name = node_output.source.node.name
        self.executions[node_output.execution_id][source_name] = node_output
    
    def get(self, execution_id: str) -> dict[str, NodeOutput]:
        return self.executions[execution_id]

@dataclass
class NodeRouting:
    choices: dict[str, 'Node']
    default_policy: Literal['all', 'none']
    flags: dict[str, NodeOutputFlags] = field(init=False)

    def __post_init__(self):
        self._none_item_added = True
        if self.default_policy == 'all':
            self.all()
        elif self.default_policy == 'none':
            self.end()

    def empty(self) -> bool:
        return not any(f.canceled for f in self.flags.values())

    def add(self, node_name: str) -> bool:
        if node_name in self.choices:
            if self._none_item_added:
                self.end()
            self.flags[node_name].canceled = False
            self._none_item_added = False
            return True
        raise ValueError(
            f'Node `{node_name}` is not in the routing choices of {list(self.choices.keys())}.'
        )

    def remove(self, node_name: str) -> bool:
        raise NotImplementedError

    def all(self):
        "Send to all the nodes"
        self.flags = {k: NodeOutputFlags(canceled=False) for k in self.choices.keys()}
    
    def end(self):
        "Remove all the nodes (terminal state for this node)"
        self.flags = {k: NodeOutputFlags(canceled=True) for k in self.choices.keys()}

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
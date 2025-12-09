from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, Literal
from types import MethodType
from abc import ABC
from dataclasses import dataclass
if TYPE_CHECKING:
    from src.nodes.node import Node

@dataclass
class NodeSource:
    id: str
    node: 'Node | None'

@dataclass
class NodeOutput:
    execution_id: str
    source: NodeSource
    result: Any

@dataclass
class _NodeProcessor:
    node: 'Node'
    inputs: 'NodeInputs'
    routing: 'NodeRouting'

    def inject_processor_fields(self, fields: set[str]) -> '_NodeProcessor':
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
    node: 'Node'
    _inputs: list[NodeOutput]

    def __post_init__(self):
        self._dict_inputs = {
            i.source.node.name if i.source.node else '__start__': i
            for i in self._inputs
        }

    def __getitem__(self, node_name: str) -> NodeOutput:
        if node_name in self._dict_inputs:
            return self._dict_inputs[node_name]
        raise KeyError(
            f'Input `{node_name}` not found in {self.node.name}. Available inputs are {list(self._dict_inputs.keys())}'
        )

    def __iter__(self):
        return iter(self._dict_inputs.values())
    
    @property
    def results(self) -> list[Any]:
        return [i.result for i in self._dict_inputs.values()]


@dataclass
class NodesExecutions:
    executions: dict[str, dict[str, NodeOutput]] = field(default_factory=dict)
    
    def insert(self, execution_id: str, node_output: NodeOutput):
        if execution_id not in self.executions:
            self.executions[execution_id] = {}
        source = '__input__' if node_output.source.node is None else node_output.source.node.name
        self.executions[execution_id][source] = node_output
    
    def get(self, execution_id: str) -> dict[str, NodeOutput]:
        return self.executions[execution_id]

@dataclass
class NodeRouting:
    node: 'Node'
    choices: dict[str, 'Node']
    default_policy: Literal['all', 'none']

    def __post_init__(self):
        self._item_added = False
        if self.default_policy == 'all':
            self.selected_nodes = {k: v for k, v in self.choices.items()}
        elif self.default_policy == 'none':
            self.selected_nodes = {}

    def add(self, node_name: str) -> bool:
        if not self._item_added:
            self.selected_nodes = {}
        if node_name in self.choices:
            self.selected_nodes[node_name] = self.choices[node_name]
            self._item_added = True
            return True
        raise ValueError(
            f'Node `{node_name}` is not in the routing choices of `{self.node.name}`. '
            f'Choices are {list(self.choices.keys())}'
        )

    def remove(self, node_name: str) -> bool:
        raise NotImplementedError
    
    def clear(self):
        self.selected_nodes = {}

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
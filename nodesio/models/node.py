from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, Literal
from types import MethodType
from abc import ABC
from dataclasses import dataclass
if TYPE_CHECKING:
    from nodesio.engine.node import Node

NodeExternalInput = '__input__'

@dataclass
class NodeExecutorConfig:
    deep_copy_fields: bool = False

@dataclass
class NodeIOStatus:
    execution: Literal['success', 'skipped', 'failed'] = 'success'
    message: str = ''

@dataclass
class NodeIOSource:
    id: str
    execution_id: str
    node: 'Node | None'

@dataclass
class NodeIO:
    source: NodeIOSource
    result: Any
    status: NodeIOStatus

@dataclass
class NotProcessed:
    pass
_NotProcessed = NotProcessed()

@dataclass
class NodeExecutorInputs:
    _node: 'Node'
    _inputs: list[NodeIO]

    def __post_init__(self):
        self._dict_inputs = {
            i.source.node.name if i.source.node 
            else NodeExternalInput:
            i for i in self._inputs
        }

    def __getitem__(self, node_name: str) -> NodeIO:
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
            if i.status.execution == 'success'
        ]

@dataclass
class NodeExecutorRouting:
    choices: dict[str, 'Node']
    default_policy: Literal['broadcast', 'skip']
    _node_status: dict[str, NodeIOStatus]

    def __post_init__(self):
        self._none_item_added = True
        if self.default_policy == 'broadcast':
            self._node_status = {k: NodeIOStatus(execution='success') for k in self.choices.keys()}
        elif self.default_policy == 'skip':
            self._node_status = {k: NodeIOStatus(execution='skipped') for k in self.choices.keys()}
        else:
            raise ValueError(f'Invalid routing default policy `{self.default_policy}`')

    def forward(self, node: str) -> bool:
        if node in self.choices:
            if self._none_item_added:
                self.clear()
            self._node_status[node].execution = 'success'
            self._none_item_added = False
            return True
        raise ValueError(
            f'Node `{node}` is not in the routing choices of {list(self.choices.keys())}.'
        )
    
    def skip(self, node: str) -> bool:
        if node in self.choices:
            self._node_status[node].execution = 'skipped'
            return True
        raise ValueError(
            f'Node `{node}` is not in the routing choices of {list(self.choices.keys())}.'
        )

    def broadcast(self) -> None:
        "Broadcast to all the nodes"
        for node in self.choices:
            self._node_status[node].execution = 'success'
    
    def clear(self):
        "Skip all the nodes (terminal state for this node)"
        for node in self.choices:
            self._node_status[node].execution = 'skipped'

@dataclass
class NodesExecutions:
    _executions: dict[str, dict[str, NodeIO]] = field(default_factory=dict)
    
    def __getitem__(self, execution_id: str) -> dict[str, NodeIO]:
        if execution_id not in self._executions:
            self._executions[execution_id] = {}
        return self._executions[execution_id]
    
    def __setitem__(self, execution_id: str, node_output: NodeIO):
        if execution_id not in self._executions:
            self._executions[execution_id] = {}
        self._executions[execution_id][node_output.source.node.name] = node_output # type: ignore

@dataclass
class _NodeExecutor:
    node: 'Node'
    inputs: NodeExecutorInputs
    executions: dict[str, NodeIO]
    routing: NodeExecutorRouting
    config: NodeExecutorConfig
    
    def __post_init__(self):
        self.result: Any = _NotProcessed
        if self.config.deep_copy_fields:
            self.set_attr = self._set_attr_deepcopy
        else:
            self.set_attr = self._set_attr

    def _set_attr(self, field: str):
        setattr(self, field, getattr(self.node, field))

    def _set_attr_deepcopy(self, field: str):
        setattr(self, field, copy.deepcopy(getattr(self.node, field)))
    
    def inject_executor_fields(self, fields: set[str]) -> '_NodeExecutor':
        if self.node is None:
            return self
        for f in fields:
            self.set_attr(f)
        self.execute = MethodType(self.node.execute.__func__, self)
        return self
    
    async def execute(self) -> Any:
        raise NotImplementedError('Replace this method with your own logic')

# @dataclass(kw_only=True)
# class NodeExecutor(ABC):
#     node: 'Node' = field(init=False, repr=False)
#     inputs: NodeExecutorInputs = field(init=False, repr=False)
#     executions: dict[str, NodeIO] = field(init=False, repr=False)
#     routing: NodeExecutorRouting = field(init=False, repr=False)
#     config: NodeExecutorConfig = field(init=False, repr=False)

#     def __post_init__(self):
#         self.config = getattr(self, 'config', NodeExecutorConfig())
    
#     @abstractmethod
#     async def execute(self) -> Any:
#         ...


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
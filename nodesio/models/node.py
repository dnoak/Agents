from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
import copy
from dataclasses import dataclass, field
import datetime
import time
from typing import Any, TYPE_CHECKING, Literal, overload
from types import MethodType
from abc import ABC
from dataclasses import dataclass
if TYPE_CHECKING:
    from nodesio.engine.node import Node

NodeExternalInput = '__input__'

@dataclass
class NodeIOStatus:
    execution: Literal['success', 'skipped', 'failed'] = 'success'
    message: str = ''

@dataclass
class NodeIOSource:
    session_id: str
    execution_id: str
    node: 'Node | None'

@dataclass
class NodeIO:
    source: NodeIOSource
    result: Any
    status: NodeIOStatus

@dataclass
class NodeExecutorInputs:
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
            f'Input `{node_name}` not found. Available inputs are {list(self._dict_inputs.keys())}'
        )

    def __iter__(self):
        return iter(self._dict_inputs.values())
    
    @property
    def results(self) -> list[Any]:
        return [
            i.result for i in self._dict_inputs.values()
            if i.status.execution == 'success'
        ]

class AllNodesRoutes:
    pass

@dataclass
class NodeExecutorRouting:
    choices: dict[str, NodeIOStatus]

    @overload
    def route(self, nodes: str): ...
    @overload
    def route(self, nodes: list[str]): ...
    @overload
    def route(self, nodes: AllNodesRoutes = AllNodesRoutes()): ...             
    @overload
    def skip(self, nodes: str): ...
    @overload
    def skip(self, nodes: list[str]): ...
    @overload
    def skip(self, nodes: AllNodesRoutes = AllNodesRoutes()): ...

    def _nodes_routing_list(self, nodes: str | list[str] | AllNodesRoutes) -> list[str]:
        if isinstance(nodes, str):
            return [nodes]
        elif isinstance(nodes, list):
            return nodes
        elif isinstance(nodes, AllNodesRoutes):
            return list(self.choices.keys())
        raise ValueError(f'Invalid nodes routing type `{type(nodes)}`')
    
    def route(self, nodes: str | list[str] | AllNodesRoutes = AllNodesRoutes()):
        forward_nodes = self._nodes_routing_list(nodes)
        for node in forward_nodes:
            if node not in self.choices:
                raise ValueError(f'Node `{node}` is not a valid routing in {list(self.choices.keys())}.')
            self.choices[node].execution = 'success'
    
    def skip(self, nodes: str | list[str] | AllNodesRoutes = AllNodesRoutes()):
        skip_nodes = self._nodes_routing_list(nodes)
        for node in skip_nodes:
            if node not in self.choices:
                raise ValueError(f'Node `{node}` is not a valid routing in {list(self.choices.keys())}.')
            self.choices[node].execution = 'skipped'

@dataclass
class NodesExecutions:
    ttl: float

    def  __post_init__(self):
        self.executions: dict[str, dict[str, NodeIO]] = defaultdict(dict)
        # self.executions: dict[str, dict[str, NodeIO]] = {}
        self.last_updates: dict[str, float] = {}

    def __len__(self):
        return len(self.executions)
    
    def __getitem__(self, execution_id: str) -> dict[str, NodeIO]:
        if execution_id not in self.executions:
            self.executions[execution_id] = {}
        return self.executions[execution_id]
    
    def __setitem__(self, execution_id: str, node_output: NodeIO):
        self.executions[execution_id][node_output.source.node.name] = node_output # type: ignore
        self.last_updates[execution_id] = time.time()
    
    async def _ttl_trigger(self):
        while True:
            await asyncio.sleep(self.ttl)
            now = time.time()
            expired_executions = [
                k for k, v in self.last_updates.items() if
                v + self.ttl < now
            ]
            for execution_id in expired_executions:
                del self.executions[execution_id]
                del self.last_updates[execution_id]


@dataclass
class NodeExecutorConfig:
    execution_ttl: float = 300

@dataclass
class NotProcessed: ...
_NotProcessed = NotProcessed()

@dataclass
class NodeExecutor:
    node: 'Node'
    inputs: NodeExecutorInputs
    executions: dict[str, NodeIO]
    routing: NodeExecutorRouting
    config: NodeExecutorConfig
    
    def __post_init__(self):
        self.result: Any = _NotProcessed

    def _set_attr_deepcopy(self, field: str):
        setattr(self, field, copy.deepcopy(getattr(self.node, field)))
    
    def inject_custom_fields(self, fields: list[tuple[str, Any]]) -> 'NodeExecutor':
        if not fields:
            for f in self.node._custom_executor_field_names:
                setattr(self, f, copy.deepcopy(getattr(self.node, f)))
        else:
            for name, value in fields:
                setattr(self, name, value)
        
        self.execute = MethodType(self.node.execute.__func__, self)
        return self
    
    async def execute(self) -> Any:
        raise NotImplementedError('Replace this method with your own logic')

class NodeAttributes:
    @property
    def digraph_graph(self) -> dict:
        return {
            'size': '500,500',
            'bgcolor': '#353B41',
        }
    
    @property
    def digraph_node(self) -> dict:
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
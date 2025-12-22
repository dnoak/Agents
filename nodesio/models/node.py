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
from nodesio.engine.workflow import Execution
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
class NodeExecutorConfig:
    execution_ttl: float = 300

@dataclass
class NotProcessed:
    pass
_NotProcessed = NotProcessed()

@dataclass
class NodeExecutor:
    node: 'Node'
    session_id: str
    execution_id: str
    inputs: NodeExecutorInputs
    execution: Execution
    routing: NodeExecutorRouting
    config: NodeExecutorConfig
    
    def __post_init__(self):
        self.result: Any = _NotProcessed

    def _set_attr_deepcopy(self, field: str):
        setattr(self, field, copy.deepcopy(getattr(self.node, field)))
    
    def inject_custom_fields(self, fields: list[tuple[str, Any]] | None) -> 'NodeExecutor':
        # print(f'🟢 Injecting custom fields on {self.node.name}')
        # print(fields)
        if fields is None:
            for f in self.node._custom_executor_field_names:
                setattr(self, f, copy.deepcopy(getattr(self.node, f)))
        else:
            for name, value in fields:
                setattr(self, name, value)
        
        self.execute = MethodType(self.node.execute.__func__, self)
        return self
    
    async def execute(self) -> Any:
        raise NotImplementedError('Replace this method with your own logic')

class GraphvizAttributes:
    def html_plot(self, svg: str) -> str:
        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Workflow</title>
                <style>
                    body {{ margin:0; background:#353B41; }}
                    svg {{ width:100vw; height:100vh; }}
                </style>
            </head>
            <body>
                {svg}
            </body>
            </html>
            """

    def graph(self) -> dict:
        return {
            'bgcolor': '#353B41',
            'rankdir': 'LR',
            'nodesep': '0.9',
            'ranksep': '1.2',
            'fontname': 'Helvetica',
        }
    
    def node(self, name: str, output_schema: Any) -> dict:
        return {
            'shape': 'record',
            'color': 'royalblue',
            'style': 'rounded,filled',
            'label': f"""
                <<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
                    <TR>
                        <TD COLSPAN="1" BGCOLOR="royalblue">
                            <FONT POINT-SIZE="50.0" COLOR="white">{name}</FONT>
                        </TD>
                    </TR>
                    <TR>
                        <TD PORT="here" BGCOLOR="#444444">
                            <FONT POINT-SIZE="30.0" COLOR="white">{output_schema.__name__}</FONT>
                        </TD>
                    </TR>
                </TABLE>>
            """.strip(),
        }

    def edge(self, output_schema: Any) -> dict:
        return {
            # 'label': output_schema.__name__,
            # 'labelfloat': 'true',
            'color': '#a9a9a9',
            'fontcolor': '#ffffff',
            'penwidth': '1.4',
            'fontsize': '11',
            'fontname': 'Helvetica',
        }

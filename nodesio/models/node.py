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
import nodesio.engine.node as nodesio_engine
if TYPE_CHECKING:
    from nodesio.engine.node import Node
    from nodesio.engine.workflow import Workflow, Execution, Session

NodeExternalInput = '__input__'

@dataclass
class NotProcessed:
    pass
_NotProcessed = NotProcessed()

@dataclass
class NodeExecutorConfig:
    """
    routing_default_policy:
        0: clear all the routes before inserting new routes
        1: broadcast to all nodes
        2: skip all nodes
    """
    routing_default_policy: Literal['broadcast', 'clear'] = 'broadcast'
    # execution_ttl: float = 300
    ...

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
    status: NodeIOStatus
    output: Any

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
    
    def __len__(self):
        return len(self._dict_inputs)

    def __iter__(self):
        return iter(self._dict_inputs.values())
    
    @property
    def outputs(self) -> list[Any]:
        return [
            i.output for i in self._dict_inputs.values()
            if i.status.execution == 'success'
        ]

class AllNodes:
    pass

@dataclass
class NodeExecutorRouting:
    choices: dict[str, NodeIOStatus]
    default_policy: Literal['broadcast', 'clear']

    def __post_init__(self):
        if self.default_policy == 'broadcast':
            self.broadcast()
        elif self.default_policy == 'clear':
            self.clear()
        else:
            raise ValueError(f'Invalid routing default policy `{self.default_policy}`')

    @overload
    def add(self, nodes: str): ... 
    @overload
    def add(self, nodes: list[str]): ...           
    @overload
    def skip(self, nodes: str): ...
    @overload
    def skip(self, nodes: list[str]): ...

    def _nodes_routing_list(self, nodes: str | list[str]) -> list[str]:
        if isinstance(nodes, str):
            return [nodes]
        elif isinstance(nodes, list):
            return nodes
        elif isinstance(nodes, AllNodes):
            return list(self.choices.keys())
        raise ValueError(f'Invalid nodes routing type `{type(nodes)}`')
    
    def add(self, nodes: str | list[str]):
        forward_nodes = self._nodes_routing_list(nodes)
        for node in forward_nodes:
            if node not in self.choices:
                raise ValueError(f'Node `{node}` is not a valid routing in {list(self.choices.keys())}.')
            self.choices[node].execution = 'success'

    def broadcast(self):
        for node in self.choices:
            self.choices[node].execution = 'success'
    
    def skip(self, nodes: str | list[str]):
        skip_nodes = self._nodes_routing_list(nodes)
        for node in skip_nodes:
            if node not in self.choices:
                raise ValueError(f'Node `{node}` is not a valid routing in {list(self.choices.keys())}.')
            self.choices[node].execution = 'skipped'

    def clear(self):
        for node in self.choices:
            self.choices[node].execution = 'skipped'
    
@dataclass
class NodeExecutorContext:
    inputs: NodeExecutorInputs
    session: 'Session'
    execution: 'Execution'
    workflow: 'Workflow'
    routing: NodeExecutorRouting

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

    def node(self, name: str, output_schema: str, methods: set[str]) -> dict:
        table = '\n'.join([
            f"""
            <TR>
                <TD PORT="here" BGCOLOR={"\"#2954A5\"" if i%2==0 else "\"#1F458C\""}>
                    <FONT POINT-SIZE="20.0" COLOR="white">{tool}</FONT>
                </TD>
            </TR>
            """.strip()
            for i, tool in enumerate(methods)
        ])
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
                    {table}
                    <TR>
                        <TD COLSPAN="1" BGCOLOR="#DA4933">
                            <FONT POINT-SIZE="30.0" COLOR="white">{output_schema}</FONT>
                        </TD>
                    </TR>
                </TABLE>>
            """.strip(),
        }

    def edge(self, output_schema: Any) -> dict:
        return {
            'color': '#a9a9a9',
            'fontcolor': "#FFFFFF",
            'penwidth': '1.4',
            'fontsize': '11',
            'fontname': 'Helvetica',
        }

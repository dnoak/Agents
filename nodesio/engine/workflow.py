import asyncio
from contextlib import asynccontextmanager
import copy
from dataclasses import dataclass, field
import dataclasses
from io import BytesIO
import tempfile
import time
from types import MethodType
from typing import Any, TYPE_CHECKING, Literal
import webbrowser
import graphviz
from collections import deque
from rich import print
from PIL import Image
import nodesio.engine.node as nodesio_engine
if TYPE_CHECKING:
    from nodesio.engine.node import Node
    from nodesio.models.node import NodeIO, GraphvizAttributes

@dataclass
class SessionMemory:
    executor_attributes: dict[str, list[tuple[str, Any]]] = field(default_factory=dict)
    messages: deque[dict[str, Any]] = field(default_factory=deque)
    facts: list[str] = field(default_factory=list)

@dataclass
class Execution:
    id: str 
    nodes: dict[str, 'NodeIO'] = field(default_factory=dict)
    running_nodes: set[str] = field(default_factory=set)
    
    @asynccontextmanager
    async def running_node(self, node_name: str):
        self.running_nodes.add(node_name)
        yield
        self.running_nodes.remove(node_name)

@dataclass
class Executions:
    _executions: dict[str, Execution]
    
    def __getitem__(self) -> Execution:
        ...

# @dataclass
# class Session:
#     # id: str
#     # executions: dict[str, Execution] = field(default_factory=dict)
#     # memory: SessionMemory = field(default_factory=SessionMemory)
#     # updated_at: float = field(default_factory=time.time)

#     def create_session(
#             self,
#             base_nodes: dict[str, Node],
#             connections_schema: dict[Literal['inputs'] | Literal['outputs'], str]    
#         ):

#     def __getitem__(self, session_id: str) -> Node:
#         session = self._sessions.get(session_id)

@dataclass
class Workflow:
    session_ttl: float
    graphviz_attributes: 'GraphvizAttributes'
    
    def __post_init__(self):
        self.sessions: dict[str, dict[str, 'Node']] = {}
        self.active: bool = False
        self._constructor_nodes: list['Node'] = []
        self._node_factory = type('_', (nodesio_engine.Node,), {})

    def __contains__(self, session_id: str):
        return session_id in self.sessions

    def __getitem__(self, session_id: str) -> dict[str, 'Node']:
        return self.sessions[session_id]
    
    def create_session(self, session_id: str):
        session_nodes: dict[str, 'Node'] = {
            node.name: self._node_factory(name=node.name, _constructor_node=False)
            for node in self._constructor_nodes
        }
        for cnode in self._constructor_nodes:
            snode = session_nodes[cnode.name]
            for attr_name in cnode._custom_attr_names:
                setattr(
                    snode, attr_name,
                    copy.deepcopy(getattr(cnode, attr_name))
                )
            for method_name in cnode._custom_methods_names:
                setattr(
                    snode, method_name,
                    MethodType(getattr(cnode, method_name).__func__, snode)
                )
            for constructor_input in cnode._input_nodes:
                snode._input_nodes.append(session_nodes[constructor_input.name])
            for constructor_output in cnode._output_nodes:
                snode._output_nodes.append(session_nodes[constructor_output.name])
        self.sessions[session_id] = session_nodes
    
    def create_graph(self):
        graph: graphviz.Digraph = graphviz.Digraph(
            graph_attr=self.graphviz_attributes.graph()
        )
        for node in self._constructor_nodes:
            graph.node(
                name=node.name,
                **self.graphviz_attributes.node(
                    name=node.name,
                    output_schema=node._output_schema.__name__,
                    tools=node._custom_methods_names - {'execute'},
                )
            )
            for output_node in node._output_nodes:
                graph.edge(
                    tail_name=node.name,
                    head_name=output_node.name,
                    **self.graphviz_attributes.edge(node._output_schema)
                )
        return graph

    def plot(self, mode: Literal['html', 'image'] = 'image', wait: float = 0.2):
        graph = self.create_graph()
        if mode == 'image':
            Image.open(BytesIO(graph.pipe(format='png'))).show(title='Workflow')
            time.sleep(wait)
        elif mode == 'html':
            svg = graph.pipe(format='svg').decode('utf-8')
            html = self.graphviz_attributes.html_plot(svg)
            with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".html",
                    delete=False,
                    encoding="utf-8"
                ) as f:
                f.write(html)
                path = f.name
            webbrowser.open(f"file:///{path}")
        else: 
            raise ValueError(f'Invalid mode `{mode}`')
    
    # def __getitem__(self, session_id: str) -> Session:
    #     session = self.sessions.get(session_id)
    #     if session is None:
    #         session = Session(id=session_id)
    #         self.sessions[session_id] = session
    #         return session
    #     session.updated_at = time.time()
    #     return session
    
    def add_execution(self, output: 'NodeIO'):
        sid = output.source.session_id
        eid = output.source.execution_id
        self.sessions[sid].executions[eid].nodes[output.source.node.name] = output # type: ignore

    # async def start(self):
    #     while True:
    #         await asyncio.sleep(self.session_ttl)
    #         now = time.time()
    #         delete = []
    #         for session in self.sessions.values():
    #             if session.updated_at + self.session_ttl < now:
    #                 delete.append(session.id)
    #         for session_id in delete:
    #             del self.sessions[session_id]
    

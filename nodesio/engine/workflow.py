import asyncio
from contextlib import asynccontextmanager
import copy
from dataclasses import dataclass, field
import dataclasses
from io import BytesIO
import tempfile
import time
from types import MethodType
from typing import Any, TYPE_CHECKING, Iterator, Literal
import webbrowser
import graphviz
from collections import deque
from rich import print
from PIL import Image
import nodesio.engine.node as nodesio_engine
from nodesio.models.node import NodeIO, GraphvizAttributes
if TYPE_CHECKING:
    from nodesio.engine.node import Node

@dataclass
class SessionMemory:
    messages: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=10))
    facts: list[Any] = field(default_factory=list)
    shared: dict[str, Any] = field(default_factory=dict)
    
@dataclass
class Execution:
    id: str 
    nodes: dict[str, 'NodeIO'] = field(default_factory=dict)
    
    def __getitem__(self, node_name: str) -> 'NodeIO':
        return self.nodes[node_name]
    
    def __setitem__(self, execution_id: str, result: 'NodeIO'):
        self.nodes[execution_id] = result

    def __iter__(self) -> Iterator['NodeIO']:
        return iter(self.nodes.values())

@dataclass
class Session:
    id: str
    nodes: dict[str, 'Node']
    executions: dict[str, Execution] = field(default_factory=dict)
    memory: SessionMemory = field(default_factory=SessionMemory)
    _last_updated: int = field(default_factory=time.monotonic_ns)

    def __getattr__(self, attr: str):
        if attr == '_last_updated':
            return self._last_updated
        self._last_updated = time.monotonic_ns()
        return getattr(self.nodes, attr)

@dataclass
class Workflow:
    def __post_init__(self):
        self.is_active: bool = False
        self.sessions: dict[str, Session] = {}
        self.sessions_ttl: float | None = 300 
        self._graphviz_attributes: GraphvizAttributes = GraphvizAttributes()
        self._constructor_nodes: list['Node'] = []
        self._node_factory = type('Node', (nodesio_engine.Node,), {'execute': None})

    def _create_session(self, session_id: str) -> Session:
        session_nodes: dict[str, 'Node'] = {}
        for node in self._constructor_nodes:
            self._node_factory.__name__ = node.__class__.__name__
            session_nodes[node.name] = self._node_factory(
                name=node.name, 
                _constructor_node=False
            )
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
        self.sessions[session_id] = Session(id=session_id, nodes=session_nodes)
        return self.sessions[session_id]
    
    def _get_session(self, session_id: str, execution_id: str) -> Session:
        session = self.sessions.get(session_id)
        if session is None:
            session = self._create_session(session_id)
        if execution_id not in session.executions:
            session.executions[execution_id] = Execution(id=execution_id)
        return session
    
    def create_graph(self, show_methods: bool):
        graph: graphviz.Digraph = graphviz.Digraph(
            graph_attr=self._graphviz_attributes.graph()
        )
        for node in self._constructor_nodes:
            methods = (node._custom_methods_names - {'execute'}) if show_methods else set()
            graph.node(
                name=node.name,
                **self._graphviz_attributes.node(
                    name=node.name,
                    output_schema=node._output_schema.__name__,
                    methods=methods,
                )
            )
            for output_node in node._output_nodes:
                graph.edge(
                    tail_name=node.name,
                    head_name=output_node.name,
                    **self._graphviz_attributes.edge(node._output_schema)
                )
        return graph

    def plot(self, mode: Literal['html', 'image'] = 'image', show_methods: bool = True, wait: float = 0.2):
        graph = self.create_graph(show_methods=show_methods)
        if mode == 'image':
            Image.open(BytesIO(graph.pipe(format='png'))).show(title='Workflow')
            time.sleep(wait)
        elif mode == 'html':
            svg = graph.pipe(format='svg').decode('utf-8')
            html = self._graphviz_attributes.html_plot(svg)
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
    
    async def start_ttl_trigger(self):
        if self.sessions_ttl is None:
            return
        while True:
            await asyncio.sleep(self.sessions_ttl)
            now = time.monotonic_ns()
            delete = []
            for session in self.sessions.values():
                if session._last_updated + self.sessions_ttl < now:
                    delete.append(session.id)
            for session_id in delete:
                del self.sessions[session_id]
    

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import time
from typing import Any, TYPE_CHECKING
import graphviz
from collections import defaultdict as ddict, deque
from rich import print
if TYPE_CHECKING:
    from nodesio.models.node import NodeIO

@dataclass
class ExecutionMemory:
    messages: deque[dict[str, Any]] = field(default_factory=deque)
    facts: list[str] = field(default_factory=list)

@dataclass
class Execution:
    id: str
    nodes: dict[str, 'NodeIO'] = field(default_factory=dict)
    nodes_executor_fields: dict[str, list[tuple[str, Any]]] = field(default_factory=dict)
    memory: ExecutionMemory = field(default_factory=ExecutionMemory)
    running_nodes: set[str] = field(default_factory=set)

    @asynccontextmanager
    async def running_node(self, node_name: str):
        self.running_nodes.add(node_name)
        yield
        self.running_nodes.remove(node_name)

@dataclass
class Session:
    id: str
    executions: dict[str, Execution] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def __getitem__(self, execution_id: str) -> Execution:
        execution = self.executions.get(execution_id)
        if execution is None:
            execution = Execution(id=execution_id)
            self.executions[execution_id] = execution
        return execution

@dataclass
class Workflow:
    node_names: list[str]
    graph: graphviz.Digraph
    session_ttl: float
    sessions: dict[str, Session] = field(default_factory=dict)
    active: bool = False
    
    def __getitem__(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)
        if session is None:
            session = Session(id=session_id)
            self.sessions[session_id] = session
            return session
        session.updated_at = time.time()
        return session
    
    def add_execution(self, output: 'NodeIO'):
        sid = output.source.session_id
        eid = output.source.execution_id
        self.sessions[sid].executions[eid].nodes[output.source.node.name] = output # type: ignore

    async def start(self):
        while True:
            await asyncio.sleep(self.session_ttl)
            now = time.time()
            delete = []
            for session in self.sessions.values():
                if session.updated_at + self.session_ttl < now:
                    delete.append(session.id)
            for session_id in delete:
                del self.sessions[session_id]
    
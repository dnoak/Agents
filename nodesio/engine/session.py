from dataclasses import dataclass, field
import datetime
import time
from typing import Any
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nodesio.engine.node import NodeExecutor
    from nodesio.models.node import NodeIO

@dataclass
class NodeSession:
    session_id: str
    executions: dict[str, 'NodeIO'] = field(default_factory=dict)
    executor_fields: list[tuple[str, Any]] | None = None
    last_update: datetime.datetime = field(default_factory=datetime.datetime.now)

    def update_fields(self, field_names: set[str], executor: 'NodeExecutor'):
        self.executor_fields = [
            (name, getattr(executor, name)) for name in field_names
        ]

    def insert_execution(self, execution_id: str, output: NodeIO):
        # self.executions.append(execution_id)
        self.executions[execution_id] = output
        self.last_update = datetime.datetime.now()

@dataclass
class SessionManager:
    ttl: float
    sessions: dict[str, NodeSession] = field(default_factory=dict)

    def exists(self, session_id: str) -> bool:
        return session_id in self.sessions

    def get_session(self, session_id: str) -> NodeSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = NodeSession(session_id=session_id)
        self.sessions[session_id].last_update = datetime.datetime.now()
        return self.sessions[session_id]
    
    def create_session(self, session_id: str):
        self.sessions[session_id] = NodeSession(session_id=session_id)
    
    async def _ttl_trigger(self):
        while True:
            await asyncio.sleep(self.ttl)

            now = datetime.datetime.now()

            expired_sessions = [
                k for k, v in self.sessions.items() if
                v.last_update + datetime.timedelta(seconds=self.ttl) < now
            ]
            for session_id in expired_sessions:
                del self.sessions[session_id]
                




            


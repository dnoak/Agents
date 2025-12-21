import asyncio
import heapq
import time
import itertools
from typing import Callable, Any
from dataclasses import dataclass, field
from collections import deque
from typing import Any
from nodesio.models.node import NodeIO

@dataclass
class _ScheduledItem:
    callback: Callable[[], Any]
    cancelled: bool = False

class DeadlineScheduler:
    def __init__(self):
        self._heap = []
        self._counter = itertools.count()
        self._lock = asyncio.Lock()
        self._task = None
        self._running = False
        self.expired_count = 0

    async def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def schedule(self, delay: float, callback):
        item = _ScheduledItem(callback=callback)
        entry = (time.time() + delay, next(self._counter), item)
        async with self._lock:
            heapq.heappush(self._heap, entry)
        return item

    def cancel(self, item: _ScheduledItem):
        item.cancelled = True

    async def _loop(self):
        try:
            while self._running:
                async with self._lock:
                    if not self._heap:
                        sleep = None
                    else:
                        deadline, _, _ = self._heap[0]
                        sleep = max(0, deadline - time.time())

                if sleep is None:
                    await asyncio.sleep(0.1)
                    continue

                await asyncio.sleep(sleep)

                now = time.time()
                async with self._lock:
                    while self._heap and self._heap[0][0] <= now:
                        _, _, item = heapq.heappop(self._heap)
                        if item.cancelled:
                            continue
                        self.expired_count += 1
                        item.callback()
        except asyncio.CancelledError:
            pass

class SlidingSessionTimer:
    def __init__(self, scheduler: DeadlineScheduler, ttl: float, on_expire: Callable[[], None]):
        self._scheduler = scheduler
        self._ttl = ttl
        self._on_expire = on_expire
        self._item: _ScheduledItem | None = None

    async def touch(self):
        if self._item:
            self._scheduler.cancel(self._item)
        self._item = await self._scheduler.schedule(self._ttl, self._on_expire)

@dataclass
class ExecutionMemory:
    messages: deque[dict[str, Any]] = field(default_factory=deque)
    facts: list[str] = field(default_factory=list)

@dataclass
class Execution:
    id: str
    nodes: dict[str, NodeIO] = field(default_factory=dict)
    memory: ExecutionMemory = field(default_factory=ExecutionMemory)

@dataclass
class Session:
    id: str
    executions: deque[Execution] = field(default_factory=deque)
    timer: SlidingSessionTimer | None = None
    ttl: float = 10

@dataclass
class Workflow:
    execution_ttl: float
    session_ttl: float
    sessions: dict[str, Session] = field(default_factory=dict)

    def __post_init__(self):
        self.scheduler = DeadlineScheduler()

    async def start(self):
        await self.scheduler.start()

    async def get_session(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)

        if not session:
            session = Session(ttl=self.session_ttl)

            async def expire_session():
                self.sessions.pop(session_id, None)

            session.timer = SlidingSessionTimer(
                self.scheduler,
                self.session_ttl,
                expire_session
            )
            self.sessions[session_id] = session

        # touch = estende TTL + GC lazy
        await session.timer.touch()
        self._gc_executions(session)

        return session

    async def get_execution(self, session_id: str, execution_id: str) -> Execution:
        session = await self.get_session(session_id)

        execution = session.executions.get(execution_id)
        if execution:
            return execution

        def expire_execution():
            session.executions.pop(execution_id, None)

        execution = Execution(ttl=self.execution_ttl)
        execution.timer = ExecutionTimer(
            self.scheduler,
            self.execution_ttl,
            expire_execution
        )
        await execution.timer.arm()

        session.executions[execution_id] = execution
        return execution

    def _gc_executions(self, session: Session):
        # GC lazy: remove executions já expiradas (timer cancelado / removido)
        dead = [
            k for k, v in session.executions.items()
            if v.timer and v.timer._item and v.timer._item.cancelled
        ]
        for k in dead:
            session.executions.pop(k, None)

import asyncio
import time
from rich import print

async def test_workflow():
    print("[bold green]START TEST[/bold green]")

    wf = Workflow(
        execution_ttl=2.0,   # execution morre em 2s
        session_ttl=3.0      # session morre se ficar 3s idle
    )

    await wf.start()

    print("\n[cyan]Criando session S1 e execution E1[/cyan]")
    e1 = await wf.get_execution("S1", "E1")

    await asyncio.sleep(1)

    print("\n[cyan]Tocando session S1 (estende TTL)[/cyan]")
    await wf.get_session("S1")

    await asyncio.sleep(1.5)

    print("\n[yellow]Depois de ~2.5s[/yellow]")
    print("Sessions:", list(wf.sessions.keys()))
    print("Executions:", list(wf.sessions["S1"].executions.keys()))

    print("\n[cyan]Criando execution E2[/cyan]")
    e2 = await wf.get_execution("S1", "E2")

    await asyncio.sleep(2.5)

    print("\n[yellow]Depois de ~5s[/yellow]")
    print("Sessions:", list(wf.sessions.keys()))
    if "S1" in wf.sessions:
        print("Executions:", list(wf.sessions["S1"].executions.keys()))
    else:
        print("Session S1 expirou")

    await asyncio.sleep(2)

    print("\n[red]Depois de ~7s[/red]")
    print("Sessions:", list(wf.sessions.keys()))

    print("\n[bold green]END TEST[/bold green]")

asyncio.run(test_workflow())

import random
from nodesio.engine.node import Node
from nodesio.models.node import (
    NodeExecutorConfig,
    NodeIO, 
    NotProcessed,
    NodeIOStatus, 
    NodeExecutorContext,
    NodeIOSource,
)
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print

@dataclass
class LimitedCounter(Node):
    count: int = 0 

    async def execute(self, ctx: NodeExecutorContext) -> int:
        if self.count >= 3:
            ctx.routing.skip()
            return self.count
        self.count += 1
        return self.count
    
a = LimitedCounter(name='a')
b = LimitedCounter(name='b')
c = LimitedCounter(name='c')

a.connect(b).connect(c)
sessions = [f's{i}' for i in range(100)]

async def main():
    for n in range(5):
        random.shuffle(sessions)
        for session in sessions:
            if random.choice([True, False]):
                continue
            res = await a.run(NodeIO(
                source=NodeIOSource(session_id=session, execution_id=f'1', node=None),
                result='🟢',
                status=NodeIOStatus(),
            ))
            print(f'{session}: {res[0].result}')
            if isinstance(res[0].result, NotProcessed):
                continue
            assert res[0].result <= 3

asyncio.run(main())
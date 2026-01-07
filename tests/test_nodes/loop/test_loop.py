import asyncio
from dataclasses import dataclass, field
import time
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeExecutorConfig, AllNodesRoutes, NotProcessed
from rich import print

@dataclass
class Alphabet(Node):
    count: int = 0

    async def execute(self, ctx) -> int:
        self.count += 1
        ctx.execution['a']
        return sum(ctx.inputs.results)

a = Alphabet(name='a')
b1 = Alphabet(name='b1')
b2 = Alphabet(name='b2')
c = Alphabet(name='c')
d = Alphabet(name='d')

a.connect(b1)
a.connect(b2)
b1.connect(c)
b2.connect(c)
c.connect(d)

a.plot()
import random
import time
from typing import ClassVar
from nodesio.models.node import NodeIO, NodeIOStatus, NodeExecutorConfig, NodeExternalInput, NodeIOSource
from nodesio.engine.node import Node
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print

@dataclass
class Alphabet(Node):
    async def execute(self, ctx) -> str:
        ... # 🥵 processa algo
        # if self.name == 'a':
        #     ctx.routing.skip('d')
        # print(ctx.workflow.sessions)
        
        return ' → '.join(ctx.inputs.results + [self.name])

a = Alphabet(name='a')
b = Alphabet(name='b')
c = Alphabet(name='c')
d = Alphabet(name='d')
e = Alphabet(name='e')
f = Alphabet(name='f')
g = Alphabet(name='g')

a.connect(b)
b.connect(c)
a.connect(d)
d.connect(e)
d.connect(f)
c.connect(g)
e.connect(g)
f.connect(g)

# a.plot()

Node.workflow.sessions_ttl = 2

async def main():
    res = await a.run(NodeIO(
        source=NodeIOSource(session_id=f'1', execution_id=f'1', node=None),
        result='__start__',
        status=NodeIOStatus(),
    ))
    print(res)
    res = await a.run(NodeIO(
        source=NodeIOSource(session_id=f'1', execution_id=f'2', node=None),
        result='__start__',
        status=NodeIOStatus(),
    ))
    print(res)


asyncio.run(main())
    
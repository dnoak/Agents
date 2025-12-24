import random
from nodesio.engine.node import Node
from nodesio.models.node import (
    NodeExecutorConfig,
    NodeIO, 
    NodeIOStatus, 
    NodeIOSource,
)
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print

@dataclass
class   Alphabet(Node):
    track: list[str] = field(default_factory=list)
    # config = NodeExecutorConfig(execution_ttl=1)
    
    async def tool2(self):
        return 1
    
    async def tool(self) -> list[str]:
        return sum(self.inputs.results, []) + self.track

    async def execute(self) -> list[str]:
        await asyncio.sleep(random.uniform(0, 1))
        if self.session_id == 's1':
            await asyncio.sleep(random.uniform(0, 1))

        sess_emoji = {'s1': '🟢', 's2': '🔴', 's3': '🟡'}[self.session_id]
        print(f'{sess_emoji} {self.name}_{self.session_id}_{self.execution_id}')
        self.track.append(f'{self.name}_{self.session_id}_{self.execution_id}')
        return await self.tool()

a = Alphabet(name='a')
b = Alphabet(name='b')
c = Alphabet(name='c')
d = Alphabet(name='d')
e = Alphabet(name='e')
f = Alphabet(name='f')
g = Alphabet(name='g')

a.connect(b)
a.connect(c)
b.connect(d)
c.connect(d)
d.connect(e)
e.connect(f)
d.connect(g)
f.connect(g)

a.plot()

async def main():
    runs = [
        a.run(NodeIO(
            source=NodeIOSource(session_id=f's1', execution_id=f'1', node=None),
            result=[],
            status=NodeIOStatus(),
        )),
        a.run(NodeIO(
            source=NodeIOSource(session_id=f's1', execution_id=f'2', node=None),
            result=[],
            status=NodeIOStatus(),
        )),
        a.run(NodeIO(
            source=NodeIOSource(session_id=f's1', execution_id=f'3', node=None),
            result=[],
            status=NodeIOStatus(),  
        ))
    ]
    print(sum(await asyncio.gather(*runs), []))

    
# asyncio.run(main())


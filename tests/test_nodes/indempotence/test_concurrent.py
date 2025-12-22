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
class Alphabet(Node):
    track: list[str] = field(default_factory=list)
    # config = NodeExecutorConfig(execution_ttl=1)

    async def execute(self) -> list[str]:
        await asyncio.sleep(random.uniform(0, 1))
        if self.session_id == 's1':
            await asyncio.sleep(random.uniform(0, 1))

        sess_emoji = {'s1': '🟢', 's2': '🔴', 's3': '🟡'}[self.session_id]
        print(f'{sess_emoji} {self.name}_{self.session_id}_{self.execution_id}')
        self.track.append(f'{self.name}_{self.session_id}_{self.execution_id}')
        return sum(self.inputs.results, []) + self.track

a = Alphabet(name='a')
b = Alphabet(name='bb')
c = Alphabet(name='ccc')
d = Alphabet(name='dddd')
e = Alphabet(name='eeeee')
f = Alphabet(name='ffffff')
g = Alphabet(name='gggggg')

a.connect(b)
a.connect(c)
b.connect(d)
c.connect(d)

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


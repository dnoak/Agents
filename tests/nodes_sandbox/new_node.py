import asyncio
from dataclasses import dataclass, field
import time
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeExecutorConfig
from rich import print

@dataclass
class Alphabet(Node):
    rere: str
    config = NodeExecutorConfig(deep_copy_fields=True)

    async def execute(self) -> str:
        if self.name == 'd':
            self.routing.clear()
        return 'Hello world!'

a = Alphabet(name='a', rere='rere')
b = Alphabet(name='b', rere='rere')
c = Alphabet(name='c', rere='rere')
d = Alphabet(name='d', rere='rere')
e = Alphabet(name='e', rere='rere')
f = Alphabet(name='f', rere='rere')
g = Alphabet(name='g', rere='rere')

a.connect(b)
b.connect(c)
a.connect(d)
d.connect(e)
d.connect(f)
e.connect(g)
f.connect(g)

a.plot()

print(a.config)
print(b.config)
print(c.config)

async def main():
    res = await a.run(NodeIO(
        source=NodeIOSource(id='user', execution_id='user', node=None),
        result='Hello world!',
        status=NodeIOStatus(),
    ))
    print(res)

asyncio.run(main())

import asyncio
from dataclasses import dataclass, field
import time
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeExecutorConfig, AllNodesRoutes
from rich import print
from pympler import asizeof

@dataclass
class Alphabet(Node):
    rere: str
    config = NodeExecutorConfig(deep_copy_fields=True)

    async def execute(self) -> str:
        # if self.name == 'd':
        #     self.routing.skip()
        #     self.routing.forward('e')
        return ' → '.join(self.inputs.results + [self.name])

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

# a.plot(sleep=0.5)

async def main():
    runs = [
            a.run(NodeIO(
            source=NodeIOSource(session_id=str(sid), execution_id=str(sid), node=None),
            result='__start__',
            status=NodeIOStatus(),
        ))
        for sid in range(10000)
    ]
    res = sum(await asyncio.gather(*runs), [])
    # print(res)

asyncio.run(main())


# total = 0
# for node in [a, b, c, d, e, f, g]:
#     print(f'[node {node.name}] Memory usage (mb): {asizeof.asizeof(a) / (1024 ** 2)}')
#     total += asizeof.asizeof(a) / (1024 ** 2)
# print(f'Total memory usage (mb): {total}')


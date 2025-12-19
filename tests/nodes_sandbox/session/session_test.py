import asyncio
from dataclasses import dataclass, field
import time
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeExecutorConfig, AllNodesRoutes, NotProcessed
from rich import print
from pympler import asizeof

@dataclass
class Alphabet(Node):
    count: int = 0
    config = NodeExecutorConfig(persist_memory_in_session=True)

    async def execute(self) -> int:
        print(self.inputs.results)
        result = sum(self.inputs.results) + self.count
        self.count += 1
        return result

a = Alphabet(name='a')
b = Alphabet(name='b')
c = Alphabet(name='c')
# d = Alphabet(name='d')
# e = Alphabet(name='e')
# f = Alphabet(name='f')
# g = Alphabet(name='g')

a.connect(b)
b.connect(c)
# c.connect(e)
# a.connect(d)
# d.connect(e)
# d.connect(f)
# e.connect(g)
# f.connect(g)
# 
# a.plot(sleep=0.5)

# print(a.config)

executions = [0, 100, 200, 300, 400]
print(executions)

async def main():
    for exec in executions:
        print(f'Execution {exec}')
        res = await a.run(NodeIO(
            source=NodeIOSource(session_id='same_session', execution_id=str(exec), node=None),
            result=exec,
            status=NodeIOStatus(),
        ))
        # print(res)
    # print(a._executions)

asyncio.run(main())


# total = 0
# for node in [a, b, c, d, e, f, g]:
#     print(f'[node {node.name}] Memory usage (mb): {asizeof.asizeof(a) / (1024 ** 2)}')
#     total += asizeof.asizeof(a) / (1024 ** 2)
# print(f'Total memory usage (mb): {total}')


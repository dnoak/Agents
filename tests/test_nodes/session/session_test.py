import asyncio
from dataclasses import dataclass, field
import time
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeExecutorConfig, AllNodesRoutes, NotProcessed
from rich import print

@dataclass
class Alphabet(Node):
    count: int = 0
    # config = NodeExecutorConfig(execution_ttl=1)

    async def execute(self, ctx) -> int:
        self.count += 1
        ctx.workflow.sessions[ctx.session.id]
        return sum(ctx.inputs.results)

a = Alphabet(name='a')
b = Alphabet(name='b')
c = Alphabet(name='c')
# d = Alphabet(name='d')
# e = Alphabet(name='e')
# f = Alphabet(name='f')
# g = Alphabet(name='g')

Node.workflow.sessions_ttl = 2

# a.connect(b)
# b.connect(c)
# c.connect(e)
# a.connect(d)
# d.connect(e)
# d.connect(f)
# e.connect(g)
# f.connect(g)
# 
# a.plot(sleep=0.5)

# print(a.config)

executions = [100, 200, 300, 400, 500]
# print(executions)

async def main():
    for hundred_exec in executions:
        for i in range(int(hundred_exec / 10)):
            res = await a.run(NodeIO(
                source=NodeIOSource(session_id=f'session_{hundred_exec}', execution_id=f'{hundred_exec}_{i}', node=None),
                result=hundred_exec + i,
                status=NodeIOStatus(),
            ))
            # print(a._running_executions)
            print(res)
            # input()
    # print(a._graph_executions['300_0'])
    while True:
        # print(list(a._graph_executions.executions.keys()))
        print(f'Sessions: {len(a.workflow.sessions)}')
        print(f'Executions: {sum(len(v.executions) for v in a.workflow.sessions.values())}')
        # print(len(a._running_executions))
        # print(sum(len(v) for v in a._running_executions.values()))
        # print()
        await asyncio.sleep(0.2)
    # print(a._sessions['session_100'].executions)
    # print(a._sessions_manager.get_session('session_100').executions)

asyncio.run(main())


# total = 0
# for node in [a, b, c, d, e, f, g]:
#     print(f'[node {node.name}] Memory usage (mb): {asizeof.asizeof(a) / (1024 ** 2)}')
#     total += asizeof.asizeof(a) / (1024 ** 2)
# print(f'Total memory usage (mb): {total}')


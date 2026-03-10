import asyncio
from nodesIO.engine.node import Node
from nodesIO.models.node import NodeIO, NodeIOStatus, NodeIOSource
from dataclasses import dataclass
from rich import print

@dataclass
class Concatenator(Node):
    async def execute(self, ctx) -> list[str]:
        raise NotImplementedError
        return sum([i.output for i in ctx.inputs], []) + [self.name] # flatten
    
a = Concatenator(name='a')
b = Concatenator(name='b')
c = Concatenator(name='c')
a.connect(b)
b.connect(c)

async def main():
    result = await a.run(NodeIO(
        source=NodeIOSource(session_id='session_1', execution_id='exec_1', node=None),
        status=NodeIOStatus(),
        output=['🟢'],
    ))
    print(result)
asyncio.run(main())

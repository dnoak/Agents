import asyncio
from nodesIO.engine.node import Node
from nodesIO.models.node import NodeIO, NodeIOStatus, NodeIOSource
from dataclasses import dataclass
from rich import print

@dataclass
class Start(Node):
    async def execute(self, ctx) -> str:
        ctx.execution
        ctx.routing.clear()
        ctx.routing.clear
        if ctx.inputs.outputs[0] == 'A':
            ctx.routing.add('a')
        elif ctx.inputs.outputs[0] == 'B':
            ctx.routing.add('b')
        return 'No branch'

@dataclass
class A(Node):
    async def execute(self, ctx) -> str:
        return 'A branch'

@dataclass
class B(Node):
    async def execute(self, ctx) -> str:
        return 'B branch'

start = Start(name='start')
a = A(name='a')
b = B(name='b')

start.connect(a)
start.connect(b)

async def main():
    for input in ['A', 'B', 'C']:
        result = await start.run(
            NodeIO(
                source=NodeIOSource(session_id='session_1', execution_id='exec_1', node=None),
                status=NodeIOStatus(),
                output=input,
            )
        )
        a.plot()
        print(f'{input=}; {result[0].output=}')
        print(f'{input=}; {result[1].output=}\n')
asyncio.run(main())
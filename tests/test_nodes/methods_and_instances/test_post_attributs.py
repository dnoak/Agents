import asyncio
from dataclasses import dataclass, field
import random
import time
from nodesIO.engine.node import Node
from nodesIO.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeExecutorConfig, NotProcessed
from rich import print

@dataclass
class Alphabet(Node):
    count: int = 0

    def _internal_test_1(self):
        print(f'🔥 Creating attribute {self.name} with value {self.count}')

    def _internal_test_2(self):
        print(f'🔥 Creating attribute {self.name} with value {self.count}')

    def external_test_3(self):
        print(f'🔥 Creating attribute {self.name} with value {self.count}')

    def external_test_4(self):
        print(f'🔥 Creating attribute {self.name} with value {self.count}')

    def create_internal_attribute(self, name: str, value: str):
        print(f'🔥 Creating attribute {name} with value {value}')
        setattr(self, name, value)

    async def execute(self, ctx) -> int:
        if self.count == 0:
            self.create_internal_attribute(f"attr_{self.name}", f'{ctx.session.id}_{ctx.execution.id}')
        print(self.attr_a)
        self.count += 1
        ctx.workflow.sessions[ctx.session.id]
        return sum(ctx.inputs.outputs)

a = Alphabet(name='a')

a.plot(wait=0.5)

async def main():
    res11 = await a.run(NodeIO(
        source=NodeIOSource(session_id='session_1', execution_id='1', node=None),
        status=NodeIOStatus(),
        output=100,
    ))
    res12 = await a.run(NodeIO(
        source=NodeIOSource(session_id='session_1', execution_id='2', node=None),
        status=NodeIOStatus(),
        output=100,
    ))
    res21 = await a.run(NodeIO(
        source=NodeIOSource(session_id='session_2', execution_id='1', node=None),
        status=NodeIOStatus(),
        output=200,
    ))
    res22 = await a.run(NodeIO(
        source=NodeIOSource(session_id='session_2', execution_id='2', node=None),
        status=NodeIOStatus(),
        output=200,
    ))
    # print(a.__dict__)
    # print(res)

asyncio.run(main())
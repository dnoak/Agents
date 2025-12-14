import random
from nodes.models.node import NodeIOFlags
from nodes.engine.node import Node, NodeIO, NodeOperator, NodeIOSource
from dataclasses import dataclass
from pydantic import BaseModel
import asyncio
from rich import print

global_counter = 0

@dataclass
class A(NodeOperator):
    async def execute(self) -> str:
        return ' -> '.join(self.inputs.results + [self.node.name])

@dataclass
class B(NodeOperator):
    async def execute(self) -> str:
        global global_counter
        print(f'\ngc: {global_counter}')
        if global_counter < 2:
            self.routing.remove('c')
        
        else:
            self.routing.add('c')
        
        global_counter += 1
        return ' -> '.join(self.inputs.results + [f'gc: {global_counter}']) 

@dataclass
class C(NodeOperator):
    async def execute(self) -> str:
        return ' -> '.join(self.inputs.results + [self.node.name])

a = Node(name="a", operator=A())
b = Node(name="b", operator=B())
c = Node(name="c", operator=C())

a.connect(b).connect(c)
# print(a.output_nodes)
# a.plot()

async def main():
    for i in range(3):
        res = await a.run(NodeIO(
            source=NodeIOSource(id='user_1', execution_id=f'exec_{i}', node=None),
            result='__start__',
            flags=NodeIOFlags(),
        ))
        print(res)


asyncio.run(main())
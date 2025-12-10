import random
from src.models.node import NodeOutputFlags
from src.nodes.node import Node, NodeProcessor, NodeSource
from dataclasses import dataclass
from pydantic import BaseModel
import asyncio
from rich import print

@dataclass
class A(NodeProcessor):
    async def execute(self) -> list[str]:
        self.routing.add('d')
        # self.routing.add('b')
        # self.routing.add('c')
        # self.routing.add('c')
        # self.routing.end()
        # self.routing.all()
        # print('⚠️ A processor')
        return sum(self.inputs.results, []) + [self.node.name]

@dataclass
class B(NodeProcessor):
    async def execute(self) -> list[str]:
        # print('⚠️ B processor')
        # self.routing.end()
        # await asyncio.sleep(random.choice([1, 2, 3]))
        return sum(self.inputs.results, []) + [self.node.name]

@dataclass
class C(NodeProcessor):
    async def execute(self) -> list[str]:
        # print('⚠️ C processor')
        return sum(self.inputs.results, []) + [self.node.name]

@dataclass
class D(NodeProcessor):
    async def execute(self) -> list[str]:
        # self.routing.end()
        # print('⚠️ D processor')
        return sum(self.inputs.results, []) + [self.node.name]

@dataclass
class E(NodeProcessor):
    async def execute(self) -> list[str]:
        # print('⚠️ E processor')
        # self.routing.end()
        return sum(self.inputs.results, []) + [self.node.name]

@dataclass
class F(NodeProcessor):
    async def execute(self) -> list[str]:
        # print('⚠️ F processor')
        # print([i for i in self.inputs])
        # print(self.inputs['b'])
        return sum(self.inputs.results, []) + [self.node.name]

@dataclass
class G(NodeProcessor):
    async def execute(self) -> list[str]:
        return sum(self.inputs.results, []) + [self.node.name]

async def main():
    a = Node(name="a", processor=A())
    b = Node(name="b", processor=B())
    c = Node(name="c", processor=C())
    d = Node(name="d", processor=D())
    e = Node(name="e", processor=E())
    f = Node(name="f", processor=F())
    g = Node(name="g", processor=G())
    
    a.connect(b).connect(f)
    a.connect(c).connect(f)
    a.connect(d).connect(e)
    e.connect(g)
    f.connect(g)
    # e.connect(f)
    # a.connect(b).connect(f)
    # a.connect(c).connect(f)
    # a.connect(d).connect(f)
    # a.connect(e).connect(f)

    a.plot()


    res1 = a.run(
        input=['input'],
        execution_id='exec_1',
        source=NodeSource(id='user_1', node=None),
        flags=NodeOutputFlags(),
    )

    # res2 = a.run(
    #     input='input',
    #     execution_id='exec_2',
    #     source=NodeSource(id='user_2', node=None),
    #     flags=NodeOutputFlags(),
    # )

    res = await asyncio.gather(res1)
    print(res[0])
    


asyncio.run(main())
from src.node import Node, NodeProcessor, NodeSource
from dataclasses import dataclass
import asyncio
from rich import print

@dataclass
class Classifier(NodeProcessor):
    async def execute(self) -> str:
        if self.inputs['__start__'].result == '1':
            self.routing.set('choice_1')
            return self.node.name
        elif self.inputs['__start__'].result == '2':
            self.routing.set('choice_2')
            return self.node.name
        else:
            raise ValueError('Invalid input')

@dataclass
class Choice(NodeProcessor):
    async def execute(self) -> str:
        x = self.inputs['classifier']
        node_choice = ''
        for result in self.inputs.results:
           node_choice = result
        return f'{node_choice} -> {self.node.name}'

@dataclass
class Merge(NodeProcessor):
    async def execute(self) -> str:
        return ''.join(self.inputs.results)

async def main():
    nc = Node(
        name='classifier',
        processor=Classifier(),
    )
    n1 = Node(
        name='choice_1',
        processor=Choice(),
    )
    n2 = Node(
        name='choice_2',
        processor=Choice(),
    )
    nm = Node(
        name='merge',
        processor=Merge(),
    )
    nc.connect(n1)
    nc.connect(n2)
    n1.connect(nm, required=False)
    n2.connect(nm, required=False)
    nc.plot()

    res = await nc.run(
        input='1',
        execution_id='exec_1',
        source=NodeSource(id='user_1', node=None),
    )
    print(res)
    print(res[0].result)

if __name__ == '__main__':
    asyncio.run(main())
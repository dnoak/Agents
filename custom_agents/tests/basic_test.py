from src.nodes.node import Node, NodeProcessor, NodeSource
from dataclasses import dataclass
from pydantic import BaseModel
import asyncio
from rich import print

async def main():
    class OutputProcessor(BaseModel):
        result: str
    
    @dataclass
    class Processor1234(NodeProcessor):
        teste: int = 1

        async def execute(self) -> OutputProcessor:
            print(self.teste)
            total = []
            for result in self.inputs.results:
                total.append(result)
            total.append(self.node.name)
            return OutputProcessor(result=' -> '.join(total))
    
    @dataclass
    class Processor5(NodeProcessor):
        async def execute(self) -> dict[int, str]:
            total: list[str] = []
            n1: OutputProcessor = self.inputs['agent1'].result
            n2: OutputProcessor = self.inputs['agent2'].result
            n3: OutputProcessor = self.inputs['agent3'].result
            n4: OutputProcessor = self.inputs['agent4'].result
            total.append(n1.result)
            total.append(n2.result)
            total.append(n3.result)
            total.append(n4.result)
            total.append(self.node.name)
            return {len(''.join(total)): ' -> '.join(total)}
    
    agent1 = Node(
        name='agent1',
        processor=Processor1234(3),
    )
    agent2 = Node(
        name='agent2',
        processor=Processor1234(4),
    )
    agent3 = Node(
        name='agent3',
        processor=Processor1234(),
    )
    agent4 = Node(
        name='agent4',
        processor=Processor1234(),
    )
    agent5 = Node(
        name='agent5',
        processor=Processor5(),
    )
    agent1.connect(agent5)
    agent2.connect(agent5)
    agent3.connect(agent5)
    agent4.connect(agent5)
    # agent1.connect(agent2).connect(agent3).connect(agent4).connect(agent5)
    # agent1.plot()

    # A
    #      ↗ 2 ↘
    # 1 ->       -> 4 -> 5
    #      ↘ 3 ↗
    
    res = [
        agent1.run(
            input='input1',
            execution_id='exec_1',
            source=NodeSource(id='user_1', node=None),
        ),
        agent2.run(
            input='input2',
            execution_id='exec_1',
            source=NodeSource(id='user_2', node=None),
        ),
        agent3.run(
            input='input3',
            execution_id='exec_1',
            source=NodeSource(id='user_3', node=None),
        ),
        agent4.run(
            input='input3',
            execution_id='exec_1',
            source=NodeSource(id='user_4', node=None),
        ),
    ]
    res = sum(await asyncio.gather(*res), [])
    
    print(res)
    # print(agent1.executions.get('exec_1'))

if __name__ == '__main__':
    asyncio.run(main())
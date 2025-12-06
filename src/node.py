from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pydantic import BaseModel
from PIL import Image
from io import BytesIO
import uuid
import asyncio
import numpy as np
import cv2
import graphviz
from rich import print

@dataclass
class NodeForwardRules:
    replicator: bool | None = None
    classifier: list[str] | None = None
    n_first: int | None = None

@dataclass
class NodeProcessor(ABC):
    @abstractmethod
    async def process(self, prev_results: list['NodeOutput']) -> int:
        ...

class NodeOutputSchema(BaseModel):
    ...

@dataclass
class NodeOutput:
    execution_id: str
    source: 'Node | None'
    result: int

# @dataclass
# class Execution:
#     id: str
#     nodes: dict[str, NodeOutput] = field(default_factory=dict)

@dataclass
class Executions:
    def __post_init__(self):
        self.executions: dict[str, dict[str, NodeOutput]] = {}
    
    def insert(self, execution_id: str, node_output: NodeOutput):
        print('🔴')
        if execution_id not in self.executions:
            self.executions[execution_id] = {}
        source = '__input__' if node_output.source is None else node_output.source.name
        self.executions[execution_id][source] = node_output
    
    def get(self, execution_id: str) -> dict[str, NodeOutput]:
        return self.executions[execution_id]


@dataclass(kw_only=True)
class Node:
    name: str
    output_schema: type[NodeOutputSchema]
    processor: NodeProcessor
    num_workers: int
    
    def __post_init__(self):
        from src.input_queue import InputQueue
        self._init_graph_globals()
        self._assert_unique_name()
        self.inputs_queue: InputQueue = InputQueue(node=self)
        self.output_nodes: list[Node] = []
        self.input_nodes: list[Node] = []
        self.required_input_nodes_ids: set[str] = set()
        self.running: bool = False

    def _init_graph_globals(self):
        if not hasattr(Node, 'names'):
            Node.names = []
        if not hasattr(Node, 'executions'):
            Node.executions: Executions = Executions()
    
    def _assert_unique_name(self):
        if self.name in Node.names:
            raise ValueError(f'Agent name `{self.name}` already exists')
        Node.names.append(self.name)
    
    def connect(self, node: 'Node', required: bool = True):
        self.output_nodes.append(node)
        node.input_nodes.append(self)
        if required:
            node.required_input_nodes_ids.add(self.name)

    # async def forward(self, result: list[NodeOutput]) -> Messages:
    #     return processed

    async def run(self, input: NodeOutput) -> list[NodeOutput]:
        self.inputs_queue.put(input)
        if self.running:
            return []
        self.running = True
        
        inputs = await self.inputs_queue.get()
        processed = await self.processor.process(
            prev_results=inputs
        )
        result = NodeOutput(
            execution_id=input.execution_id,
            source=self,
            result=processed,
        )
        Node.executions.insert(input.execution_id, result)

        forward_nodes = [node.run(result) for node in self.output_nodes]
        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        return [result]        

async def main():
    
    class AgentOutput(NodeOutputSchema):
        result: int

    class AgentProcessor(NodeProcessor):
        async def process(self, prev_results: list['NodeOutput']) -> int:
            total = 0
            for pv in prev_results:
                # print(pv.source.name if pv.source else 'start', pv.result)
                total += pv.result
            # print(total)
            return total
    
    agent1 = Node(
        name='agent1',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
        num_workers=1,
    )
    agent2 = Node(
        name='agent2',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
        num_workers=1,
    )
    agent3 = Node(
        name='agent3',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
        num_workers=1,
    )
    agent4 = Node(
        name='agent4',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
        num_workers=1,
    )
    agent5 = Node(
        name='agent5',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
        num_workers=1,
    )
    agent1.connect(agent5)
    agent2.connect(agent5)
    agent3.connect(agent5)
    agent4.connect(agent5)
    # agent5.connect(agent1)

    

    # A
    #      ↗ 2 ↘
    # 1 ->       -> 4 -> 5
    #      ↘ 3 ↗
    res = [
        agent1.run(NodeOutput(
            execution_id='exec_1',
            source=None,
            result=1,
        )),
        agent2.run(NodeOutput(
            execution_id='exec_1',
            source=None,
            result=1,
        )),
        agent3.run(NodeOutput(
            execution_id='exec_1',
            source=None,
            result=1,
        )),
        agent4.run(NodeOutput(
            execution_id='exec_1',
            source=None,
            result=1,
        )),
    ]
    res = sum(await asyncio.gather(*res), [])
    
    print(res)
    print(agent1.executions.get('exec_1'))

if __name__ == '__main__':
    asyncio.run(main())
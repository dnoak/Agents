from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar
from pydantic import BaseModel
from PIL import Image
from io import BytesIO
import uuid
import asyncio
import numpy as np
import cv2
import graphviz
from rich import print
from src.input_queue import InputQueue
from models.node import (
    NodeProcessor,
    NodeOutputSchema,
    NodeOutput,
    NodesExecutions,
    NodeRouting,
    NodeReplicator,
)

@dataclass(kw_only=True)
class Node:
    name: str
    output_schema: type[NodeOutputSchema]
    processor: NodeProcessor
    
    graph_attr: ClassVar[dict[str, str]] = {
        'size': '500,500',
        'bgcolor': '#353B41',
    }
    
    def __post_init__(self):
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
            Node.executions: NodesExecutions = NodesExecutions()
        if not hasattr(Node, 'graph'):
            Node.graph = graphviz.Digraph(graph_attr=self.graph_attr)
        Node.graph.node(
            name=self.name,
            label=self.output_schema.node_label(self), 
            **self.output_schema.node_attributes(),
        )
    
    def _assert_unique_name(self):
        if self.name in Node.names:
            raise ValueError(f'Agent name `{self.name}` already exists')
        Node.names.append(self.name)

    def plot(self, animate: bool = False):
        if not animate:
            return Image.open(BytesIO(Node.graph.pipe(format='png'))).show()
        def update_graph():
            while True:
                data = Node.graph.pipe(format='jpeg', engine='dot') # 0.2 ~ 0.3s por frame
                img_np = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                cv2.namedWindow("Graph Animation", cv2.WINDOW_AUTOSIZE)
                cv2.imshow("Graph Animation", img_np)
                if cv2.waitKey(500) & 0xFF == 27:
                    break
            cv2.destroyAllWindows()
        Node.animate = True
        update_graph()

    def connect(self, node: 'Node', required: bool = True):
        self.output_nodes.append(node)
        node.input_nodes.append(self)
        if required:
            node.required_input_nodes_ids.add(self.name)
        attributes = self.output_schema.edge_attributes()
        if not required:
            attributes['style'] = 'dashed'
            attributes['arrowhead'] = 'odot'
        Node.graph.edge(
            tail_name=self.name,
            head_name=node.name, 
            **attributes
        )
        return node

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
                total += pv.result
            return total
    
    agent1 = Node(
        name='agent1',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
    )
    agent2 = Node(
        name='agent2',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
    )
    agent3 = Node(
        name='agent3',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
    )
    agent4 = Node(
        name='agent4',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
    )
    agent5 = Node(
        name='agent5',
        output_schema=AgentOutput,
        processor=AgentProcessor(),
    )
    agent1.connect(agent5)
    agent2.connect(agent5)
    agent3.connect(agent5)
    agent4.connect(agent5)
    # agent1.connect(agent2).connect(agent3).connect(agent4).connect(agent5)
    agent1.plot()
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
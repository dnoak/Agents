from dataclasses import dataclass, field
from typing import Any, Literal, get_type_hints
from pydantic import BaseModel
from PIL import Image
from io import BytesIO
import dataclasses
import uuid
import asyncio
import numpy as np
import cv2
import graphviz
from rich import print
from src.input_queue import InputQueue
from models.node import (
    _NodeProcessor,
    NodeProcessor,
    NodeAttributes,
    NodeOutput,
    NodeSource,
    NodeRouting,
    NodeInputs,
    NodesExecutions,
)

@dataclass
class Node:
    name: str
    processor: NodeProcessor
    attributes: NodeAttributes = field(default_factory=NodeAttributes, repr=False)

    def __post_init__(self):
        self.output_schema = get_type_hints(self.processor.execute)['return']
        self.inputs_queue: InputQueue = InputQueue(node=self)
        self.output_nodes: list[Node] = []
        self.input_nodes: list[Node] = []
        self.required_input_nodes_ids: set[str] = set()
        self.running: bool = False
        self._processor_fields_to_inject = set.difference(
            set(n.name for n in dataclasses.fields(self.processor)),
            set(n.name for n in dataclasses.fields(_NodeProcessor))
        )
        self._init_graph_globals()
        self._assert_node_name()

    def _init_graph_globals(self):
        if not hasattr(Node, 'names'):
            Node.names = []
        if not hasattr(Node, 'executions'):
            Node.executions: NodesExecutions = NodesExecutions()
        if not hasattr(Node, 'graph'):
            Node.graph = graphviz.Digraph(graph_attr=self.attributes.digraph_graph)
        Node.graph.node(
            name=self.name,
            label=self.attributes.node_label(
                self.name, 
                self.output_schema,
                running=self.running,
            ), 
            **self.attributes.digraph_node,
        )
    
    def _assert_node_name(self):
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
        attributes = self.attributes.edge()
        if not required:
            attributes['style'] = 'dashed'
            attributes['arrowhead'] = 'odot'
        Node.graph.edge(
            tail_name=self.name,
            head_name=node.name, 
            **attributes
        )
        return node

    async def run(
            self,
            input: Any,
            execution_id: str,
            source: NodeSource,
        ) -> list[NodeOutput]:
        self.inputs_queue.put(NodeOutput(execution_id, source, input))
        if self.running:
            return []
        self.running = True
        
        run_inputs = await self.inputs_queue.get()
        
        processor = _NodeProcessor(
            node=self,
            # inputs={i.source.node.name if i.source.node else '__start__': i for i in run_inputs},
            inputs=NodeInputs(node=self, _inputs=run_inputs),
            routing=NodeRouting(
                node=self,
                choices={n.name: n for n in self.output_nodes},
                default_policy='all',
            ),
        ).inject_processor_fields(self._processor_fields_to_inject)

        output = NodeOutput(
            execution_id=execution_id, 
            source=NodeSource(id=execution_id, node=self), 
            result=await processor.execute()
        )
        Node.executions.insert(execution_id, output)
        forward_nodes = [
            node.run(output.result, execution_id, output.source, ) 
            for node in processor.routing.selected_nodes.values()
        ]
        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        return [output]
    




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
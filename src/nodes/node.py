from dataclasses import dataclass, field
from typing import Any, get_type_hints
from pydantic import BaseModel
from PIL import Image
from io import BytesIO
from collections import defaultdict
import dataclasses
import asyncio
import numpy as np
import cv2
import graphviz
from rich import print
from src.nodes.input_queue import InputQueue
from src.models.node import (
    _NodeProcessor,
    NodeProcessor,
    NodeAttributes,
    NodeOutput,
    NodeOutputFlags,
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
        self.is_terminal: bool = True
        self.running_executions: defaultdict[str, set[str]] = defaultdict(set)
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

    def connect(self, node: 'Node'):
        self.is_terminal = False
        self.output_nodes.append(node)
        node.input_nodes.append(self)
        attributes = self.attributes.edge()
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
            flags: NodeOutputFlags,
            source: NodeSource,
        ) -> list[NodeOutput]:

        self.inputs_queue.put(NodeOutput(
            execution_id=execution_id,
            source=source,
            result=input,
            flags=flags,
        ))
        if execution_id in self.running_executions:
            return []
        self.running_executions[execution_id].add(source.id)
        
        run_inputs = await self.inputs_queue.get(execution_id)
        assert {execution_id} == set(i.execution_id for i in run_inputs)
        
        processor = _NodeProcessor(
            node=self,
            inputs=NodeInputs(_node=self, _inputs=run_inputs),
            routing=NodeRouting(
                choices={n.name: n for n in self.output_nodes},
                default_policy='all',
            ),
        ).inject_processor_fields(self._processor_fields_to_inject)

        if not all(r.flags.canceled for r in run_inputs):
            processor.result = await processor.execute()
            flags.canceled = False
        else:
            processor.routing.end()
            flags.canceled = True

        output = NodeOutput(
            execution_id=execution_id, 
            source=NodeSource(id=execution_id, node=self),
            result=processor.result,
            flags=flags,
        )

        Node.executions.insert(output)

        forward_nodes = [
            node.run(
                input=processor.result, 
                execution_id=execution_id, 
                source=NodeSource(id=execution_id, node=self),
                flags=processor.routing.flags[node.name]
            )
            for node in self.output_nodes
        ]
        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])

        # if not self.is_terminal:
        #     if processor.routing.empty():
        #         flags.canceled = True

        # self.running_executions[execution_id].remove(source.id)
        # return [NodeOutput(
        #     execution_id=execution_id, 
        #     source=NodeSource(id=execution_id, node=self),
        #     result=processor.result,
        #     flags=flags,
        # )]

        self.running_executions[execution_id].remove(source.id)
        return [output]
    


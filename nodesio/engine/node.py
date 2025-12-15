from contextlib import contextmanager
from dataclasses import dataclass, field
import time
from typing import get_type_hints
from PIL import Image
from io import BytesIO
from collections import defaultdict
import dataclasses
import asyncio
import numpy as np
import cv2
import graphviz
from nodesio.engine.input_queue import NodeInputsQueue
from nodesio.models.node import (
    _NodeOperator,
    NodeOperator,
    NodeAttributes,
    NodeIO,
    NodeIOStatus,
    NodeIOSource,
    NodeOperatorRouting,
    NodeOperatorInputs,
    NodesExecutions,
)

@dataclass
class Node:
    name: str
    operator: NodeOperator
    attributes: NodeAttributes = field(default_factory=NodeAttributes, repr=False)
    
    def __post_init__(self):
        self.output_schema = get_type_hints(self.operator.execute)['return']
        self.inputs_queue: NodeInputsQueue = NodeInputsQueue(node=self)
        self.output_nodes: list[Node] = []
        self.input_nodes: list[Node] = []
        self.is_terminal: bool = True
        self.running_executions: defaultdict[str, set[str]] = defaultdict(set)
        self._operator_fields_to_inject: set[str] = set.difference(
            set(n.name for n in dataclasses.fields(self.operator)),
            set(n.name for n in dataclasses.fields(_NodeOperator))
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
        if not hasattr(Node, 'metrics'):
            Node.metrics = defaultdict(float)
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

    @contextmanager
    def timer(self, name='str'):
        t0 = time.perf_counter()
        yield
        t1 = time.perf_counter()
        Node.metrics[name] += (t1 - t0)
    
    @contextmanager
    def execution_running(self, execution_id='str'):
        self.running_executions[execution_id].add(self.name)
        yield
        self.running_executions[execution_id].remove(self.name)

    def plot(self, animate: bool = False):
        if not animate:
            return Image.open(BytesIO(Node.graph.pipe(format='png'))).show()

    def connect(self, node: 'Node'):
        self.is_terminal = False
        self.output_nodes.append(node)
        node.inputs_queue.sort_order.append(self.name)
        node.input_nodes.append(self)
        attributes = self.attributes.edge()
        Node.graph.edge(
            tail_name=self.name,
            head_name=node.name, 
            **attributes
        )
        return node
    
    async def _start(self, source: NodeIOSource, inputs: list[NodeIO]) -> list[NodeIO]:
        operator = _NodeOperator(
            node=self,
            inputs=NodeOperatorInputs(_node=self, _inputs=inputs),
            routing=NodeOperatorRouting(
                choices={n.name: n for n in self.output_nodes},
                default_policy='broadcast',
                _node_status={}
            ),
            config=self.operator.config
        ).inject_operator_fields(self._operator_fields_to_inject)

        # if not all(r.flags.canceled for r in inputs):
        #     operator.result = await operator.execute()
        #     flags_canceled = False
        # else:
        #     operator.routing.clear()
        #     flags_canceled = True

        if any(r.status.execution == 'success' for r in inputs):
            operator.result = await operator.execute()
            execution_status = 'success'
        else:
            operator.routing.clear()
            execution_status = 'skipped'

        output = NodeIO(
            source=source,
            result=operator.result,
            status=NodeIOStatus(execution=execution_status, message=''),
        )

        Node.executions.insert(output)

        forward_nodes = [
            node.run(
                input=NodeIO(
                    source=source,
                    result=operator.result,
                    status=operator.routing._node_status[node.name],
                )
            )
            for node in self.output_nodes
        ]

        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        
        return [output]
    
    async def run(self, input: NodeIO) -> list[NodeIO]:
        self.inputs_queue.put(NodeIO(
            source=input.source,
            result=input.result,
            status=input.status,
        ))
        
        if input.source.execution_id in self.running_executions:
            return []
        
        with self.execution_running(execution_id=input.source.execution_id):
            run_inputs = await self.inputs_queue.get(input.source.execution_id)
            output = await self._start(
                source=NodeIOSource(
                    id=input.source.id, 
                    execution_id=input.source.execution_id, 
                    node=self
                ),
                inputs=run_inputs,
            )

        return output
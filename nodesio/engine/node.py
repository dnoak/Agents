from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
import time
from typing import Any, get_type_hints
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
    _NodeExecutor,
    # NodeExecutor,
    NodeAttributes,
    NodeIO,
    NodeIOStatus,
    NodeIOSource,
    NodeExecutorRouting,
    NodeExecutorInputs,
    NodesExecutions,
    NodeExecutorConfig,
)

@dataclass
class Node(ABC):
    name: str = field(kw_only=True)
    config: NodeExecutorConfig = field(default_factory=NodeExecutorConfig, repr=False, kw_only=True)
    attributes: NodeAttributes = field(default_factory=NodeAttributes, repr=False, kw_only=True)
    inputs: NodeExecutorInputs = field(init=False, repr=False)
    executions: dict[str, NodeIO] = field(init=False, repr=False)
    routing: NodeExecutorRouting = field(init=False, repr=False)
    
    def __post_init__(self):
        self._output_schema = get_type_hints(self.execute)['return']
        self._inputs_queue: NodeInputsQueue = NodeInputsQueue(node=self)
        self._output_nodes: list[Node] = []
        self._input_nodes: list[Node] = []
        self.is_terminal: bool = True
        self._running_executions: defaultdict[str, set[str]] = defaultdict(set)
        self._operator_fields_to_inject: set[str] = set.difference(
            set(n.name for n in dataclasses.fields(self)),
            set(n.name for n in dataclasses.fields(_NodeExecutor))
        )
        self._init_graph_globals()
        self._assert_node_name()
    
    @abstractmethod
    async def execute(self) -> Any:
        ...

    def _init_graph_globals(self):
        if not hasattr(Node, 'names'):
            Node._names = []
        if not hasattr(Node, 'executions'):
            Node._executions: NodesExecutions = NodesExecutions()
        if not hasattr(Node, 'graph'):
            Node._graph = graphviz.Digraph(graph_attr=self.attributes.digraph_graph)
        if not hasattr(Node, 'metrics'):
            Node.metrics = defaultdict(float)
        Node._graph.node(
            name=self.name,
            label=self.attributes.node_label(
                self.name, 
                self._output_schema,
            ), 
            **self.attributes.digraph_node,
        )
    
    def _assert_node_name(self):
        if self.name in Node._names:
            raise ValueError(f'Node name `{self.name}` already exists')
        Node._names.append(self.name)

    @contextmanager
    def timer(self, name='str'):
        t0 = time.perf_counter()
        yield
        t1 = time.perf_counter()
        Node.metrics[name] += (t1 - t0)
    
    @contextmanager
    def execution_running(self, execution_id='str'):
        self._running_executions[execution_id].add(self.name)
        yield
        self._running_executions[execution_id].remove(self.name)

    def plot(self):
        return Image.open(BytesIO(Node._graph.pipe(format='png'))).show()

    def connect(self, node: 'Node'):
        self.is_terminal = False
        self._output_nodes.append(node)
        node._inputs_queue.sort_order.append(self.name)
        node._input_nodes.append(self)
        attributes = self.attributes.edge()
        Node._graph.edge(
            tail_name=self.name,
            head_name=node.name, 
            **attributes
        )
        return node
    
    async def _start(self, source: NodeIOSource, inputs: list[NodeIO]) -> list[NodeIO]:
        executor = _NodeExecutor(
            node=self,
            inputs=NodeExecutorInputs(_node=self, _inputs=inputs),
            executions=Node._executions[source.execution_id],
            routing=NodeExecutorRouting(
                choices={n.name: n for n in self._output_nodes},
                default_policy='broadcast',
                _node_status={}
            ),
            config=self.config
        ).inject_executor_fields(self._operator_fields_to_inject)

        if any(r.status.execution == 'success' for r in inputs):
            executor.result = await executor.execute()
            execution_status = 'success'
        else:
            executor.routing.clear()
            execution_status = 'skipped'

        output = NodeIO(
            source=source,
            result=executor.result,
            status=NodeIOStatus(execution=execution_status, message=''),
        )

        Node._executions[source.execution_id] = output

        forward_nodes = [
            node.run(
                input=NodeIO(
                    source=source,
                    result=executor.result,
                    status=executor.routing._node_status[node.name],
                )
            )
            for node in self._output_nodes
        ]

        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        
        return [output]
    
    async def run(self, input: NodeIO) -> list[NodeIO]:
        self._inputs_queue.put(NodeIO(
            source=input.source,
            result=input.result,
            status=input.status,
        ))
        
        if input.source.execution_id in self._running_executions:
            return []
        
        with self.execution_running(execution_id=input.source.execution_id):
            run_inputs = await self._inputs_queue.get(input.source.execution_id)
            output = await self._start(
                source=NodeIOSource(
                    id=input.source.id, 
                    execution_id=input.source.execution_id, 
                    node=self
                ),
                inputs=run_inputs,
            )

        return output
from dataclasses import dataclass, field
from typing import Any, get_type_hints
from contextlib import contextmanager
from collections import defaultdict
from abc import ABC, abstractmethod
from io import BytesIO
from PIL import Image
import dataclasses
import asyncio
import graphviz
import time
from nodesio.engine.inputs_queue import NodeInputsQueue
from nodesio.models.node import (
    _NotProcessed,
    NodeExecutor,
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
    config: NodeExecutorConfig = field(init=False, repr=False, kw_only=True)
    inputs: NodeExecutorInputs = field(init=False, repr=False)
    executions: dict[str, NodeIO] = field(init=False, repr=False)
    routing: NodeExecutorRouting = field(init=False, repr=False)
    
    def __post_init__(self):
        self._output_schema = get_type_hints(self.execute)['return']
        self._inputs_queue: NodeInputsQueue = NodeInputsQueue(node=self)
        self._output_nodes: list[Node] = []
        self._input_nodes: list[Node] = []
        self._running_executions: defaultdict[str, set[str]] = defaultdict(set)
        self._custom_executor_field_names: set[str] = set.difference(
            set(n.name for n in dataclasses.fields(self)),
            set(n.name for n in dataclasses.fields(NodeExecutor))
        )
        self._sessions_executor_fields: dict[str, list[tuple[str, Any]]] = defaultdict(list)
        self._set_defaults()
        self._init_graph_globals()
        self._assert_node_name()
    
    @abstractmethod
    async def execute(self) -> Any:
        ...

    def _set_defaults(self):
        self.attributes = NodeAttributes()
        if not hasattr(self, 'config'):
            self.config = NodeExecutorConfig()

    def _init_graph_globals(self):
        if not hasattr(Node, '_names'):
            Node._names = []
        if not hasattr(Node, '_executions'):
            # 🥵 bug: só o primeiro Node criado com config vai setar o TTL global
            Node._graph_executions: NodesExecutions = NodesExecutions(ttl=self.config.execution_ttl)
        if not hasattr(Node, '_graph'):
            Node._graph = graphviz.Digraph(graph_attr=self.attributes.digraph_graph)
        if not hasattr(Node, '_ttl_trigger_active'):
            Node._ttl_trigger_active = False
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
    def _running_execution(self, execution_id: str):
        self._running_executions[execution_id].add(self.name)
        yield
        self._running_executions[execution_id].remove(self.name)

    def plot(self, sleep: float = 0.2):
        Image.open(BytesIO(Node._graph.pipe(format='png'))).show(title=f'{self.name} executions')
        time.sleep(sleep)
    
    def connect(self, node: 'Node'):
        self._output_nodes.append(node)
        node._inputs_queue.sort_order.append(self.name)
        node._input_nodes.append(self)
        Node._graph.edge(
            tail_name=self.name,
            head_name=node.name, 
            **self.attributes.edge()
        )
        return node
    
    async def _start(self, source: NodeIOSource, inputs: list[NodeIO]) -> list[NodeIO]:
        executor = NodeExecutor(
            node=self,
            inputs=NodeExecutorInputs(_inputs=inputs),
            executions=Node._graph_executions[source.execution_id],
            routing=NodeExecutorRouting(choices={n.name: NodeIOStatus() for n in self._output_nodes}),
            config=self.config
        )

        if source.session_id not in self._sessions_executor_fields:
            self._sessions_executor_fields[source.session_id] = []

        executor.inject_custom_fields(self._sessions_executor_fields[source.session_id])
        
        if any(r.status.execution == 'success' for r in inputs):
            executor.result = await executor.execute()
            self._sessions_executor_fields[source.session_id] = [
                (name, getattr(executor, name)) for name in self._custom_executor_field_names
            ]
            execution_status = 'success'
        else:
            executor.routing.skip()
            execution_status = 'skipped'
            executor.result = _NotProcessed

        output = NodeIO(
            source=source,
            result=executor.result,
            status=NodeIOStatus(execution=execution_status, message=''),
        )

        Node._graph_executions[source.execution_id] = output

        forward_nodes = [
            node.run(
                input=NodeIO(
                    source=source,
                    result=executor.result,
                    status=executor.routing.choices[node.name],
                )
            )
            for node in self._output_nodes
        ]

        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        
        return [output]
    
    async def run(self, input: NodeIO) -> list[NodeIO]:
        if not Node._ttl_trigger_active:
            asyncio.create_task(Node._graph_executions._ttl_trigger())
            Node._ttl_trigger_active = True
        
        self._inputs_queue.put(NodeIO(
            source=input.source,
            result=input.result,
            status=input.status,
        ))
        
        if input.source.execution_id in self._running_executions:
            return []
        
        with self._running_execution(execution_id=input.source.execution_id):
            run_inputs = await self._inputs_queue.get(input.source.execution_id)
            output = await self._start(
                source=NodeIOSource(
                    session_id=input.source.session_id, 
                    execution_id=input.source.execution_id, 
                    node=self
                ),
                inputs=run_inputs,
            )

        return output
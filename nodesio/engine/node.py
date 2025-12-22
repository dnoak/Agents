from dataclasses import dataclass, field
from typing import Any, Literal, get_type_hints
from abc import ABC, abstractmethod
import dataclasses
import asyncio
import graphviz
from nodesio.engine.inputs_queue import NodeInputsQueue
from nodesio.engine.workflow import Execution, Workflow
from nodesio.models.node import (
    _NotProcessed,
    GraphvizAttributes,
    NodeExecutor,
    NodeIO,
    NodeIOStatus,
    NodeIOSource,
    NodeExecutorRouting,
    NodeExecutorInputs,
    # NodesExecutions,
    NodeExecutorConfig,
)

@dataclass
class NodeInterface(ABC):
    session_id: str = field(init=False, repr=False)
    execution_id: str = field(init=False, repr=False)
    inputs: NodeExecutorInputs = field(init=False, repr=False)
    execution: Execution = field(init=False, repr=False)
    routing: NodeExecutorRouting = field(init=False, repr=False)
    
    @abstractmethod
    async def execute(self) -> Any:
        ...

@dataclass(kw_only=True)
class Node(NodeInterface):
    name: str
    config: NodeExecutorConfig = field(init=False, repr=False)

    def __post_init__(self):
        self.config = self.config if hasattr(self, 'config') else NodeExecutorConfig()
        self._output_schema = get_type_hints(self.execute)['return']
        self._inputs_queue: NodeInputsQueue = NodeInputsQueue(node=self)
        self._input_nodes: list[Node] = []
        self._output_nodes: list[Node] = []
        self._custom_executor_field_names: set[str] = set.difference(
            set(n.name for n in dataclasses.fields(self)),
            set(n.name for n in dataclasses.fields(NodeExecutor))
        )
        self._init_workflow()
        self._assert_node_name()

    def _init_workflow(self):
        if not hasattr(Node, '_workflow'):
            Node._workflow = Workflow(
                session_ttl=self.config.execution_ttl,
                graphviz_attributes=GraphvizAttributes(),
            )
        Node._workflow.graph.node(
            name=self.name,
            **Node._workflow.graphviz_attributes.node(
                name=self.name, 
                output_schema=self._output_schema
            ),
        )
        
    def _assert_node_name(self):
        if self.name in Node._workflow.node_names:
            raise ValueError(f'Node name `{self.name}` already exists')
        Node._workflow.node_names.append(self.name)

    def plot(self, mode: Literal['html', 'image'] = 'image', wait: float = 0.2):
        Node._workflow.plot(mode=mode, wait=wait)

    def connect(self, node: 'Node'):
        self._output_nodes.append(node)
        node._inputs_queue.sort_order.append(self.name)
        node._input_nodes.append(self)
        Node._workflow.graph.edge(
            tail_name=self.name,
            head_name=node.name,
            **Node._workflow.graphviz_attributes.edge(self._output_schema)
        )
        return node
    
    async def _start(self, source: NodeIOSource, inputs: list[NodeIO]) -> list[NodeIO]:
        executor = NodeExecutor(
            node=self,
            session_id=source.session_id,
            execution_id=source.execution_id,
            inputs=NodeExecutorInputs(_inputs=inputs),
            execution=Node._workflow[source.session_id][source.execution_id],
            routing=NodeExecutorRouting(choices={n.name: NodeIOStatus() for n in self._output_nodes}),
            config=self.config
        )

        executor.inject_custom_fields(
            Node._workflow[source.session_id][source.execution_id]
            .nodes_executor_fields.get(self.name)
        )
        
        if any(r.status.execution == 'success' for r in inputs):
            executor.result = await executor.execute()
            Node._workflow[source.session_id][source.execution_id].nodes_executor_fields[self.name] = [
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
        Node._workflow.add_execution(output)

        forward_nodes = [
            node.run(
                input=NodeIO(
                    source=source,
                    result=executor.result,
                    status=executor.routing.choices[node.name],
                )
            ) for node in self._output_nodes
        ]
        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        return [output]
        # return sum(await asyncio.gather(*forward_nodes), []) or [output]
    
    async def run(self, input: NodeIO) -> list[NodeIO]:
        if not Node._workflow.active:
            asyncio.create_task(Node._workflow.start())
            Node._workflow.active = True

        self._inputs_queue.put(NodeIO(
            source=input.source,
            result=input.result,
            status=input.status,
        ))
        
        sid = input.source.session_id
        eid = input.source.execution_id
        
        if self.name in Node._workflow[sid][eid].running_nodes:
            return []
        
        async with Node._workflow[sid][eid].running_node(node_name=self.name):
            run_inputs = await self._inputs_queue.get(eid)
            output = await self._start(
                source=NodeIOSource(
                    session_id=sid, 
                    execution_id=eid, 
                    node=self
                ),
                inputs=run_inputs,
            )
        
        return output
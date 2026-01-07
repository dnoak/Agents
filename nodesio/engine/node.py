from dataclasses import dataclass, field
from typing import Any, Literal, get_type_hints
from abc import ABC, abstractmethod
import dataclasses
import asyncio
import inspect
from nodesio.engine.inputs_queue import NodeInputsQueue
from nodesio.engine.workflow import Workflow
from nodesio.models.node import (
    _NotProcessed,
    NodeExecutorContext,
    NodeIO,
    NodeIOStatus,
    NodeIOSource,
    NodeExecutorRouting,
    NodeExecutorInputs,
    NodeExecutorConfig,
)

@dataclass
class NodeInterface(ABC):
    @abstractmethod
    async def execute(self, ctx: NodeExecutorContext) -> Any:
        ...

@dataclass(kw_only=True)
class Node(NodeInterface):
    name: str
    config: NodeExecutorConfig = field(init=False, repr=False)
    _constructor_node: bool = field(default=True, repr=False)

    def __post_init__(self):
        self.config = self.config if hasattr(self, 'config') else NodeExecutorConfig()
        self._inputs_queue: NodeInputsQueue = NodeInputsQueue(node=self)
        self._input_nodes: list[Node] = []
        self._output_nodes: list[Node] = []
        self._running: bool = False

        if self._constructor_node:
            self._output_schema = get_type_hints(self.execute).get('return', Any)
            self._set_workflow()
            self._set_custom_data()
            self.run = self._run_in_session
    
    def _set_custom_data(self):
        self._custom_attr_names: set[str] = {
            n.name for n in dataclasses.fields(self)
        } | {'_output_schema'} - {'config'}
        self._custom_methods_names: set[str] = set.difference(
            {n[0] for n in inspect.getmembers(self, inspect.ismethod) if not n[0].startswith('_')},
            {'connect', 'plot', 'run'}
        )
    
    def _set_workflow(self):
        if not hasattr(Node, 'workflow'):
            Node.workflow = Workflow()
        
        if self.name in [cn.name for cn in Node.workflow._constructor_nodes]:
            raise ValueError(f'Node name `{self.name}` already exist in Workflow')
        Node.workflow._constructor_nodes.append(self)
    
    def plot(self, mode: Literal['html', 'image'] = 'image', show_methods: bool = True, wait: float = 0.2):
        Node.workflow.plot(mode=mode, show_methods=show_methods, wait=wait)

    def connect(self, node: 'Node'):
        self._output_nodes.append(node)
        node._input_nodes.append(self)
        return node
    
    async def _start(self, source: NodeIOSource, inputs: list[NodeIO]) -> list[NodeIO]:
        session = Node.workflow.sessions[source.session_id]
        execution = session.executions[source.execution_id]

        ctx = NodeExecutorContext(
            inputs=NodeExecutorInputs(inputs),
            session=session,
            execution=execution,
            workflow=Node.workflow,
            routing=NodeExecutorRouting(
                choices={n.name: NodeIOStatus() for n in self._output_nodes},
                default_policy=self.config.routing_default_policy
            )
        )
        if any(r.status.execution == 'success' for r in inputs):
            output = await self.execute(ctx)
            execution_status = 'success'
        else:
            ctx.routing.clear()
            output = _NotProcessed
            execution_status = 'skipped'

        result = NodeIO(
            source=source,
            status=NodeIOStatus(execution=execution_status, message=''),
            output=output,
        )
        execution[self.name] = result

        forward_nodes = [
            node.run(
                input=NodeIO(
                    source=source,
                    status=ctx.routing.choices[node.name],
                    output=output,
                )
            ) for node in self._output_nodes
        ]
        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        return [result]

    async def _run_in_session(self, input: NodeIO) -> list[NodeIO]:
        session = self.workflow._get_session(
            input.source.session_id, 
            input.source.execution_id
        )
        return await session.nodes[self.name].run(input)
    
    async def run(self, input: NodeIO) -> list[NodeIO]:
        if not Node.workflow.is_active:
            asyncio.create_task(Node.workflow.start_ttl_trigger())
            Node.workflow.is_active = True

        self._inputs_queue.put(NodeIO(
            source=input.source,
            status=input.status,
            output=input.output,
        ))
        
        sid = input.source.session_id
        eid = input.source.execution_id

        if self._running:
            return []
        
        self._running = True
        inputs = await self._inputs_queue.get(eid)
        result = await self._start(
            source=NodeIOSource(
                session_id=sid, 
                execution_id=eid, 
                node=self
            ),
            inputs=inputs,
        )
        self._running = False
        
        return result

@dataclass
class EmptyNode(Node):
    async def execute(self, ctx) -> Any: ...
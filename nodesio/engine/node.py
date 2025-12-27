import copy
from dataclasses import dataclass, field
from types import MethodType
from typing import Any, Callable, Literal, get_type_hints
from abc import ABC, abstractmethod
import dataclasses
import asyncio
import inspect
from nodesio.engine.inputs_queue import NodeInputsQueue
from nodesio.engine.workflow import Workflow
from nodesio.models.node import (
    _NotProcessed,
    GraphvizAttributes,
    NodeExecutorContext,
    NodeIO,
    NodeIOStatus,
    NodeIOSource,
    NodeExecutorRouting,
    NodeExecutorInputs,
    NodeExecutorConfig,
)

@dataclass
class NodeInterface():
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
        if not hasattr(Node, '_workflow'):
            Node._workflow = Workflow(
                session_ttl=self.config.execution_ttl,
                graphviz_attributes=GraphvizAttributes(),
            )
        if self.name in Node._workflow._constructor_nodes:
            raise ValueError(f'Node name `{self.name}` already exist in Workflow')
        Node._workflow._constructor_nodes.append(self)
    
    def plot(self, mode: Literal['html', 'image'] = 'image', wait: float = 0.2):
        Node._workflow.plot(mode=mode, wait=wait)

    def connect(self, node: 'Node'):
        self._output_nodes.append(node)
        node._input_nodes.append(self)
        return node
    
    async def _start(self, source: NodeIOSource, inputs: list[NodeIO]) -> list[NodeIO]:
        ctx = NodeExecutorContext(
            inputs=NodeExecutorInputs(inputs),
            execution_id=source.execution_id,
            session_id=source.session_id,
            routing=NodeExecutorRouting(
                choices={n.name: NodeIOStatus() for n in self._output_nodes}
            )
        )
        if any(r.status.execution == 'success' for r in inputs):
            result = await self.execute(ctx)
            execution_status = 'success'
        else:
            ctx.routing.skip()
            execution_status = 'skipped'
            result = _NotProcessed

        output = NodeIO(
            source=source,
            result=result,
            status=NodeIOStatus(execution=execution_status, message=''),
        )
        # Node._workflow.add_execution(output)

        forward_nodes = [
            node.run(
                input=NodeIO(
                    source=source,
                    result=result,
                    status=ctx.routing.choices[node.name],
                )
            ) for node in self._output_nodes
        ]
        if forward_nodes:
            return sum(await asyncio.gather(*forward_nodes), [])
        return [output]

    async def _run_in_session(self, input: NodeIO) -> list[NodeIO]:
        sid = input.source.session_id
        if sid not in self._workflow.sessions:
            self._workflow.create_session(session_id=sid)
        return await self._workflow.sessions[sid][self.name].run(input)
    
    async def run(self, input: NodeIO) -> list[NodeIO]:
        # if not Node._workflow.active:
        #     asyncio.create_task(Node._workflow.start())
        #     Node._workflow.active = True

        self._inputs_queue.put(NodeIO(
            source=input.source,
            result=input.result,
            status=input.status,
        ))
        
        sid = input.source.session_id
        eid = input.source.execution_id

        if self._running:
            return []
        
        self._running = True
        inputs = await self._inputs_queue.get(eid)
        output = await self._start(
            source=NodeIOSource(
                session_id=sid, 
                execution_id=eid, 
                node=self
            ),
            inputs=inputs,
        )
        self._running = False
        
        return output

@dataclass
class EmptyNode(Node):
    async def execute(self, ctx) -> Any: ...
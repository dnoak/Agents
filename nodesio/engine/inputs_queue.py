from dataclasses import dataclass
from collections import defaultdict
from typing import TYPE_CHECKING
from nodesio.models.node import NodeIO
if TYPE_CHECKING:
    from nodesio.engine.node import Node
import asyncio

@dataclass
class NodeInputsQueue:
    node: 'Node'
    
    def __post_init__(self):
        self.alocker = asyncio.Lock()
        self.futures: dict[str, asyncio.Future[list[NodeIO]]] = {}
        self.pending: defaultdict[str, dict[str, NodeIO]] = defaultdict(dict)
        self.required_inputs: defaultdict[str, set[str]] = defaultdict(set)
    
    def put(self, input: NodeIO):
        if input.source.node is None:
            future = asyncio.get_running_loop().create_future()
            future.set_result([input])
            self.futures[input.source.execution_id] = future
            return
        
        first_execution = input.source.execution_id not in self.pending
        if first_execution:
            self.required_inputs[input.source.execution_id] = {
                node.name for node in self.node._input_nodes
                if node.name != self.node.name
            }
            self.futures[input.source.execution_id] = asyncio.get_running_loop().create_future()
        
        if input.status.execution != 'success':
            self.required_inputs[input.source.execution_id].remove(input.source.node.name)
        
        self.pending[input.source.execution_id][input.source.node.name] = input
        
        if self.required_inputs[input.source.execution_id].issubset(
                self.pending[input.source.execution_id].keys()
            ):
            values = list(self.pending.pop(input.source.execution_id).values())
            self.futures[input.source.execution_id].set_result(values)

    async def get(self, execution_id: str) -> list[NodeIO]:
        await self.futures[execution_id]
        result = self.futures.pop(execution_id).result()
        if len(result) == 1:
            return result
        order = [i.name for i in self.node._input_nodes]
        return sorted(result, key=lambda x: order.index(x.source.node.name))
        

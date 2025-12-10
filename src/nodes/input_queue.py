from dataclasses import dataclass, field
from collections import defaultdict
from typing import TYPE_CHECKING
from config import settings
from src.models.node import NodeOutput
if TYPE_CHECKING:
    from src.nodes.node import Node
import asyncio

@dataclass
class InputQueue:
    node: 'Node'
    
    def __post_init__(self):
        self.alocker = asyncio.Lock()
        self.futures: dict[str, asyncio.Future[list[NodeOutput]]] = {}
        self.pending: defaultdict[str, dict[str, NodeOutput]] = defaultdict(dict)
        self.required_inputs: defaultdict[str, set[str]] = defaultdict(set)
        self.sort_order: list[str] = [settings.node.first_execution_source]

    def put(self, input: 'NodeOutput'):
        if input.source.node is None:
            future = asyncio.get_running_loop().create_future()
            future.set_result([input])
            self.futures[input.execution_id] = future
            return
        
        first_execution = input.execution_id not in self.pending
        if first_execution:
            self.required_inputs[input.execution_id] = {node.name for node in self.node.input_nodes}
            self.futures[input.execution_id] = asyncio.get_event_loop().create_future()
            
        if input.flags.canceled:
            self.required_inputs[input.execution_id].remove(input.source.node.name)
        
        self.pending[input.execution_id][input.source.node.name] = input
        
        if self.required_inputs[input.execution_id].issubset(
                self.pending[input.execution_id].keys()
            ):
            values = list(self.pending.pop(input.execution_id).values())
            self.futures[input.execution_id].set_result(values)

    async def get(self, execution_id: str) -> list['NodeOutput']:
        await self.futures[execution_id]
        result = self.futures.pop(execution_id).result()
        if len(result) == 1:
            return result
        return sorted(result, key=lambda x: self.sort_order.index(x.source.node.name))
        

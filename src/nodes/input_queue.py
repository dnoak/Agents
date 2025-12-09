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
        self.queue: asyncio.Queue[list[NodeOutput]] = asyncio.Queue()
        self.pending_queue: defaultdict[str, dict[str, NodeOutput]] = defaultdict(dict)
        self.required_inputs: defaultdict[str, set[str]] = defaultdict(set)

    def put(self, input: 'NodeOutput'):
        if input.source.node is None:
            self.queue.put_nowait([input])
            return
        
        if input.execution_id not in self.pending_queue:
            self.required_inputs[input.execution_id] = {node.name for node in self.node.input_nodes}
        
        if input.flags.canceled:
            self.required_inputs[input.execution_id].remove(input.source.node.name)
        
        self.pending_queue[input.execution_id][input.source.node.name] = input
        
        if self.required_inputs[input.execution_id].issubset(
                self.pending_queue[input.execution_id].keys()
            ):
            self.queue.put_nowait(list(self.pending_queue.pop(input.execution_id).values()))

    async def get(self) -> list['NodeOutput']:
        return await self.queue.get()

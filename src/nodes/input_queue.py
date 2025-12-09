from dataclasses import dataclass
from collections import defaultdict
from typing import TYPE_CHECKING
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

    def _check_inputs_trigger(self, execution_id: str) -> None:
        if self.node.required_input_nodes_ids.issubset(
                self.pending_queue[execution_id].keys()
            ):
            ready_input = self.pending_queue.pop(execution_id)
            self.queue.put_nowait(list(ready_input.values()))            
    
    def put(self, input: 'NodeOutput'):
        if input.source.node is None:
            return self.queue.put_nowait([input])
        
        self.pending_queue[input.execution_id][input.source.node.name] = input
        self._check_inputs_trigger(input.execution_id)

    async def get(self) -> list['NodeOutput']:
        return await self.queue.get()

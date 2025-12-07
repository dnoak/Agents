from __future__ import annotations
from dataclasses import dataclass
import json
from collections import defaultdict
import asyncio
from typing import TYPE_CHECKING
import time
from models.node import NodeOutput
if TYPE_CHECKING:
    from src.node import Node

@dataclass
class InputQueue:
    node: Node

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
    
    def put(self, input: NodeOutput):
        if input.source is None:
            return self.queue.put_nowait([input])
        
        self.pending_queue[input.execution_id][input.source.name] = input
        self._check_inputs_trigger(input.execution_id)

    async def get(self) -> list[NodeOutput]:
        return await self.queue.get()


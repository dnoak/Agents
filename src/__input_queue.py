from dataclasses import dataclass
import json
from collections import defaultdict
import asyncio
from termcolor import colored
from src.message import Messages
from typing import TYPE_CHECKING, Literal, Optional
import time
if TYPE_CHECKING:
    from src.agent import Agent

@dataclass
class InputQueue:
    agent: 'Agent'
    wait_time: float = 3
    response_classifier: Optional[Literal['llm', 'test']] = None

    def __post_init__(self):
        self.alocker = asyncio.Lock()
        self.queue: asyncio.Queue[list[Messages]] = asyncio.Queue()
        self.pending_inputs_queue: defaultdict[str, dict[str, Messages]] = defaultdict(dict)
        self.pending_triggers_queue: defaultdict[str, dict[str, Messages]] = defaultdict(dict)

    def _input_waited_enough(self, message_id: str) -> bool:
        # if not self.pending_queue[message_id]:
        #     return False
        for messages in self.pending_inputs_queue[message_id].values():
            print(time.time() - messages.last.timestamp)
            if time.time() - messages.last.timestamp < self.wait_time:
                return False
        return True

    def _input_is_full(self, message_id: str) -> bool:
        received_ids = {
            message.source.id for message in
            self.pending_inputs_queue[message_id].values()
            if message.source is not None
        }
        return self.agent.required_input_nodes_ids.issubset(received_ids)
    
    def _input_response_classifier(self, message_id: str) -> bool:
        for messages in self.pending_inputs_queue[message_id].values():
            if list(messages.last.content.values())[0].endswith('?'):
                return True
            if list(messages.last.content.values())[0].endswith('/end'):
                return True
        return False
    
    def _validate_schema(self, messages: Messages):
        if not messages.source: return
        try:
            messages.source.output_schema(**messages.last.content)
        except:
            received = json.dumps(messages.last.content, indent=4, ensure_ascii=False)
            expected = json.dumps(messages.source.output_schema.annotations(), indent=4, ensure_ascii=False)
            exception = colored(
                f'\n❌ ❌ ❌ Schema validation failed for agent `{self.agent.name}`:\n',
                color='red', attrs=['bold']
            )
            exception += colored(f'received:\n{received}\n', color='blue')
            exception += colored(f'expected:\n{expected}\n', color='yellow')
            raise Exception(exception)
    
    def _sort_messages(self, messages: list[Messages]) -> list[Messages]:
        id_order = {a.id: index for index, a in enumerate(self.agent.input_nodes)}
        return sorted(messages, key=lambda m: id_order[m.source.id]) # type: ignore
    
    def _triggers_queue_loop(self):
        while True:

    def put(self, messages: Messages):
        # if not self._input_waited_enough(messages.id):
        #     return
        # if not self._input_response_classifier(messages.id):
        #     return
        
        if messages.source is None:
            # print(f'🟢 ready_input from None: {messages.id}')
            # return self.queue.put_nowait([messages])
            return self.pending_triggers_queue[messages.id][messages.source] = messages
        
        if not self._input_is_full(messages.id):
            return
        
        self._validate_schema(messages)
        self.pending_inputs_queue[messages.id][messages.source.name] = messages

        # print(f'🟡 inserting {messages.id} in {self.agent.name}')
        ready_input = self.pending_inputs_queue.pop(messages.id)
        self.queue.put_nowait(self._sort_messages(list(ready_input.values())))
            # print(f'🟢 ready_input: {messages.id}')

    async def get(self) -> list[Messages]:
        async with self.alocker:
            return await self.queue.get()


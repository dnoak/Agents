from dataclasses import dataclass, field
import json
from collections import defaultdict
import asyncio
import threading
from termcolor import colored
from src.message import Message, Messages
from typing import TYPE_CHECKING, Literal, Optional
from rich import print
import time
if TYPE_CHECKING:
    from src.agent import Agent

@dataclass
class ChatTriggers:
    message_accumulator_wait_time: float = 3
    message_accumulator_timeout: float = 20
    ready_to_response_classifier: Optional[Literal['llm', 'test']] = None
    end_of_conversation_classifier: Optional[Literal['llm', 'test']] = None

@dataclass(kw_only=True)
class ChatQueue:
    messages: dict[str, Messages] = field(default_factory=dict)
    inputs_ready: bool = False
    triggers_ready: bool = False
    triggers: ChatTriggers

    def _trigger_message_accumulator_wait_time(self, messages: Messages) -> bool:
        #for messages in self.messages.values():
        passed_time = time.time() - messages.last.timestamp
        # print(f'passed_time: {passed_time}')
        if passed_time < self.triggers.message_accumulator_wait_time:
            # print(f'  🔴 remaining time: {self.triggers.message_accumulator_wait_time - passed_time}')
            return False
        # print(f'  ☑️ triggers activated for {list(self.messages.values())[0].id}')
        return True

    def update_triggers_status(self):
        for messages in self.messages.values():
            if messages.source is not None:
                continue
            if not self._trigger_message_accumulator_wait_time(messages):
                return
        self.triggers_ready = True

    def update_inputs_status(self, source: Optional['Agent'], agent: 'Agent'):
        if source is None:
            self.inputs_ready = True
            return
        received_ids = {
            messages.source.id for messages in
            self.messages.values()
            if messages.source is not None
        }
        if agent.required_input_nodes_ids.issubset(received_ids):
            self.inputs_ready = True

@dataclass
class InputQueues:
    agent: 'Agent'
    triggers: ChatTriggers

    # 🔴🔴🔴 NÃO ESQUECER DE FILTRAR APENAS MENSAGENS DO USUÁRIO NOS TRIGGERS 🔴🔴🔴

    def __post_init__(self):
        self.alocker = asyncio.Lock()
        self.locker = threading.Lock()
        self.loop: asyncio.AbstractEventLoop
        
        self.queue: asyncio.Queue[list[Messages]] = asyncio.Queue()
        self.pending_queues: dict[str, ChatQueue] = {}
        self.blocked_queues: set[str] = set()
        
        self._start()

    def _start(self):
        ready_event = threading.Event()

        def _runner():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            ready_event.set()
            self.loop.run_forever()

        threading.Thread(target=_runner, daemon=True).start()
        ready_event.wait()

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
    
    def _set_inputs_status(self, chat_id: str):
        received_ids = {
            messages.source.id for messages in
            self.pending_queues[chat_id].messages.values()
            if messages.source is not None
        }
        if self.agent.required_input_nodes_ids.issubset(received_ids):
            self.pending_queues[chat_id].inputs_ready = True

    def _sort_messages(self, messages: list[Messages]) -> list[Messages]:
        if not self.agent.input_nodes:
            return messages
        id_order = {a.id: index for index, a in enumerate(self.agent.input_nodes)}
        return sorted(messages, key=lambda m: id_order[m.source.id]) # type: ignore

    async def _trigger_loop(self, chat_id: str):
        while True:
            async with self.alocker:
               # with self.locker:
                queue = self.pending_queues[chat_id]

                self.pending_queues[chat_id].update_triggers_status()

                print(f'🟡 [3] queue: {queue.inputs_ready}')
                print(f'🟡 [3] triggers: {queue.triggers_ready}')
                print(f'🟡 [3] blocked: {chat_id in self.blocked_queues}\n')
                if queue.inputs_ready and queue.triggers_ready and chat_id not in self.blocked_queues:
                    print(f'    🟢 [4] triggers ready for {chat_id}')
                    ready_input = self.pending_queues.pop(chat_id)

                    self.block_queue(chat_id)

                    self.queue.put_nowait(
                        self._sort_messages(list(ready_input.messages.values()))
                    )
                    #print(self.queue)
                    return
            await asyncio.sleep(0.1)

    def block_queue(self, chat_id: str):
        self.blocked_queues.add(chat_id)
        print(f'🔴 [3] blocked queue for {chat_id}')
        print(self.blocked_queues)

    def unblock_queue(self, chat_id: str):
        self.blocked_queues.remove(chat_id)
        print(f'🟢 [3] unblocked queue for {chat_id}')
        print(self.blocked_queues)
    
    def put(self, messages: Messages):            
        source_name = messages.source.name if messages.source is not None else 'None'
        print(f'🟢 [1] {self.agent.name} received message from {source_name}, chat_id: {messages.id}')
        create_task = False
        with self.locker:
            if messages.id not in self.pending_queues:
                create_task = True
                self.pending_queues[messages.id] = ChatQueue(triggers=self.triggers)
                if source_name not in self.pending_queues[messages.id].messages:
                    self.pending_queues[messages.id].messages[source_name] = Messages(
                        id=messages.id,
                        data=[],
                        source=messages.source,
                    )

        print(f'    🟡 [1.1] created new task for {messages.id}: {create_task}')

        if messages.source is not None:
            self._validate_schema(messages)

        with self.locker:
            self.pending_queues[messages.id].messages[source_name].append(messages)
            self.pending_queues[messages.id].update_inputs_status(messages.source, self.agent)

            print(f'🟢 [2] added message to {messages.id}, source: {source_name}')
            print(f'    🟢 messages: {self.pending_queues[messages.id].messages[source_name].last.content}')

        if create_task and self.pending_queues[messages.id].inputs_ready:
            asyncio.run_coroutine_threadsafe(
                self._trigger_loop(messages.id),
                self.loop
            )

    async def get(self) -> list[Messages]:
        #async with self.alocker:
        return await self.queue.get()

from dataclasses import dataclass
from pydantic import BaseModel
from fastapi import FastAPI, APIRouter
from src.message import Message, Messages
from datetime import datetime


class ChatMessage(BaseModel):
    chat_id: str
    message: str

@dataclass
class MessageChannel:
    id: str
    wait_for_response: int = 3

    def __post_init__(self):
        self.messages_buffer: list[Message]
        self.router = APIRouter()
        self.router.add_api_route(
            '/send-message', self.receive, methods=['POST'],
        )

    def _waited_enough(self, messages: Messages) -> bool:
        messages.last.timestamp

    def _message_status_classifier(self, messages: Messages) -> str:
        if self.messages_buffer[-1].content.values()[0].endswith('/end'):
            return 'end_of_conversation'
        elif self.messages_buffer[-1].content.values()[0].endswith('/response'):
            return 'ready_for_response'
        else:
            return 'waiting_user_message'

    async def receive(self, chat_message: ChatMessage) -> ...:
        message = Message(
            id=chat_message.chat_id,
            content={'chat_input': chat_message.message},
            role='user',
        )

        # 🔴🔴🔴 with self.alocker:
        if message.id not in self.messages_buffer:
            self.messages_buffer[message.id] = Messages(id=message.id, data=[message])
            return {'status': '✅ first message sent'}
        else:
            self.messages_buffer[message.id].data.append(message)
            return {'status': '⌛️ message queued'}
        
    async def send(self, messages: Messages) -> ...:
        if not self._waited_enough(messages):
            return
        if self._message_status_classifier(messages) == 'end_of_conversation':
            return
        if self._message_status_classifier(messages) == 'waiting_user_message':
            return
        assert self._message_status_classifier(messages) == 'ready_for_response'

        ...



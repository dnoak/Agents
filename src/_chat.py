import asyncio
from dataclasses import dataclass
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException
from typing import Literal
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from src.agent import Agent
from dataclasses import dataclass
import os
import random
from typing import Optional
from pydantic import BaseModel, Field
from src.instructions import LlmInstructions
from src.agent import Agent
from src.llm import LLM, LlmApi
from src.message import Message, MessagesFormatter
from models.agent import Replicator, Classifier, Processor
import requests
import time
import requests

class TelegramSenderOutput(Replicator):
    response: str = Field(
        description="Resposta para o usuário." 
    )

@dataclass
class TelegramSenderProcessor(Processor):
    blocked_chats: dict[str, datetime]
    telegram_url: str = "https://api.telegram.org/bot{TOKEN}/sendMessage"

    def __post_init__(self):
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(url)
        if r.status_code == 200:
            usd_brl = r.json()['rates']['BRL']
            self.usd_brl = usd_brl
        else:
            self.usd_brl = None
    
    def unblock_chat(self, chat_id: str):
        if chat_id in self.blocked_chats:
            self.blocked_chats.pop(chat_id)

    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        costs = sum([
            m['cost'] for m in Agent.metadata[messages[0].id]
        ])
        if self.usd_brl is None:
            costs_str = f"{costs:.6f}$"
        else:
            costs_str = f"R$ {costs * self.usd_brl:.6f} (1$ = R$ {self.usd_brl})"

        requests.post(
            url=self.telegram_url.format(TOKEN=os.environ['TELEGRAM_BOT_TOKEN']),
            json={
                'chat_id': messages[0].id,
                'text': MessagesFormatter(messages).format() + f"\n\n[DEBUG]\nCosts 💰: {costs_str}",
            }
        )
        self.unblock_chat(messages[0].id)

class InputMessage(BaseModel):
    chat_id: str
    message: str

@dataclass
class TelegramChat:
    start_node: Agent
    end_nodes: list[Agent]
    all_nodes: list[Agent]
    message_lifespan: float = 10.

    def __post_init__(self):
        self.router = APIRouter()
        self.router.add_api_route(
            '/send_message', self.send_message, methods=['POST'],
        )
        self.router.add_api_route(
            '/session_cost', self.session_cost, methods=['GET'],
        )
        self.router.add_api_route(
            '/end_session', self.end_session, methods=['POST'],
        )
        self.blocked_chats: dict[str, datetime] = {}
        self.telegram_sender_agent = Agent(
            name='telegram_sender',
            role='assistant',
            output_schema=TelegramSenderOutput,
            processor=TelegramSenderProcessor(self.blocked_chats),
            num_workers=4,
        )
        self._connect_nodes()
        self.alocker = asyncio.Lock()
        self.history_queue: list[Message] = []

    def _connect_nodes(self):
        for agent in self.end_nodes:
            agent.connect(self.telegram_sender_agent, required=False)

    def _chat_is_blocked(self, chat_id: str):
        if chat_id not in self.blocked_chats:
            return False
        remaining_time = self.message_lifespan - (
            datetime.now() - self.blocked_chats[chat_id]
        ).total_seconds()
        if remaining_time <= 0:
            self.blocked_chats.pop(chat_id)
            return False
        return True
    
    async def end_session(self, chat_id: str):
        async with Agent.alocker:
            if chat_id not in Agent.metadata:
                return HTTPException(
                    status_code=404,
                    detail="❌ Chat not found"
                )
            Agent.metadata.pop(chat_id)
        return {"status": "🫡 Chat ended"}

    async def session_cost(self, chat_id: str):
        session_costs = 0
        if chat_id not in Agent.metadata:
            return HTTPException(
                status_code=404,
                detail="❌ Chat not found"
            )
        for m in Agent.metadata[chat_id]:
            session_costs += m['cost']
        return {
            "status": "💰 Chat session costs",
            "costs": f"{session_costs:.6f}",
            "currency": "USD",
        }
    
    async def send_message(self, input_message: InputMessage):
        message = Message(
            id=input_message.chat_id,
            content={'chat_input': input_message.message},
            history=[],
            role='user',
            source=None
        )
        if self._chat_is_blocked(input_message.chat_id):
            async with self.alocker:
                self.history_queue.append(message)
            return {"status": "⌛️ blocked chat, queueing message"}

        async with self.alocker:
            message.history = self.history_queue
            self.history_queue = []
        self.start_node.run(message)
        self.blocked_chats[input_message.chat_id] = datetime.now()
        return {"status": "✅ message sent"}


# if __name__ == "__main__":
from agents.nectar.input_classifier import input_classifier_fn
from agents.nectar.direct_response import direct_response_fn
from agents.nectar.blog.blog_query_rag import blog_query_rag_fn
from agents.nectar.out_of_scope_response import out_of_scope_response_fn
from agents.nectar.blog.blog_response import blog_response_fn

input_classifier = input_classifier_fn('input_classifier', False)
direct_response = direct_response_fn('direct_response')
blog_query_rag = blog_query_rag_fn('blog_query_rag')
out_of_scope_response = out_of_scope_response_fn('out_of_scope')
blog_response = blog_response_fn('blog_response')

input_classifier.connect(direct_response)
input_classifier.connect(out_of_scope_response)
input_classifier.connect(blog_query_rag)

blog_query_rag.connect(blog_response)

chat = TelegramChat(
    start_node=input_classifier,
    end_nodes=[
        direct_response,
        out_of_scope_response,
        blog_response,
    ],
    all_nodes=[
        input_classifier,
        direct_response,
        blog_query_rag,
        out_of_scope_response,
        blog_response,
    ],
    message_lifespan=10.,
)

app = FastAPI()
app.include_router(chat.router)
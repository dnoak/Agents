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
from src.message import Message, Messages
from models.agent import Replicator, Classifier, Processor
import models.chat_api
import requests
import time
import requests
from custom_agents.delay_triggers._dt import dt_agent

class TelegramSenderOutput(Replicator):
    response: str = Field(
        description="Resposta para o usuário." 
    )

@dataclass
class TelegramSenderProcessor(Processor):
    telegram_url: str = "https://api.telegram.org/bot{TOKEN}/sendMessage"

    def __post_init__(self):
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            usd_brl = r.json()['rates']['BRL']
            self.usd_brl = usd_brl
        else:
            self.usd_brl = None
    
    def process(self, agent: Agent, messages: list[Messages], llm: dict) -> dict | None:
        # print('🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴')
        # costs = sum([
        #     m['cost'] for m in Agent.metadata[messages[0].id]
        # ])
        # if self.usd_brl is None:
        #     costs_str = f"{costs:.6f}$"
        # else:
        #     costs_str = f"R$ {costs * self.usd_brl:.6f} (1$ = R$ {self.usd_brl})"

        costs_str = "💰 💰 💰"

        requests.post(
            url=self.telegram_url.format(TOKEN=os.environ['TELEGRAM_BOT_TOKEN']),
            json={
                'chat_id': messages[0].id,
                'text': str(messages[0].last.content['response']) + f"\n\n[DEBUG]\nCosts 💰: {costs_str}",
            }
        )
        agent.inputs_queue.unblock_queue(messages[0].id)

start_node = dt_agent
end_nodes = [dt_agent]
all_nodes = [dt_agent]

telegram_sender_agent = Agent(
    name='telegram_sender',
    role='assistant',
    output_schema=TelegramSenderOutput,
    processor=TelegramSenderProcessor(),
    num_workers=4,
)

for agent in end_nodes:
    agent.connect(telegram_sender_agent, required=False)

app = FastAPI()

@app.post("/send_message")
async def send_message(messages: models.chat_api.Messages):
    messages_ = Messages(
        id=messages.id,
        data=[Message(
            id=m.id,
            content=m.content,
            role=m.role,
        ) for m in messages.data],
        source=None
    )
    start_node.run(messages_)
    return {"status": "✅ message sent"}
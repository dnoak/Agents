from dataclasses import dataclass
import os
import random
from typing import Optional
from pydantic import Field
from src.instructions import LlmInstructions
from src.agent import Agent
from src.llm import LLM, LlmApi
from src.message import Message, MessagesFormatter
from models.agent import Replicator, Classifier, Processor
import requests
import time
import requests

def obter_cotacao_dolar():
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    resposta = requests.get(url)
    if resposta.status_code == 200:
        dados = resposta.json()
        cotacao_brl = dados['rates']['BRL']
        return cotacao_brl
    else:
        return None

cotacao = obter_cotacao_dolar()


class BlogResponseOutput(Replicator):
    response: str = Field(
        description="Resposta para o usuário." 
    )

class BlogResponseProcessor(Processor):
    telegram_url: str = "https://api.telegram.org/bot{TOKEN}/sendMessage"

    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        costs = sum([
            m['cost'] for m in agent.metadata[messages[0].id]
        ])
        if cotacao is None:
            costs_str = f"{costs:.6f}$"
        else:
            costs_str = f"R$ {costs * cotacao:.6f} (1$ = R$ {cotacao})"

        requests.post(
            url=self.telegram_url.format(TOKEN=os.environ['TELEGRAM_BOT_TOKEN']),
            json={
                'chat_id': messages[0].id,
                'text': MessagesFormatter(messages).format() + f"\n\n[DEBUG]\nCosts 💰: {costs_str}",
            }
        )

def telegram_sender_fn(name: str):
    return Agent(
        name=name,
        role='assistant',
        output_schema=BlogResponseOutput,
        processor=BlogResponseProcessor(),
        num_workers=4,
    )
import asyncio
import json
import os
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
# from custom_agents.math_tool.tool_sum import tool_add_fn, ToolAdd
# from custom_agents.math_tool.tool_subtract import tool_subtract_fn, ToolSubtract
from custom_agents.math_tool.tool_multiply import tool_multiply_fn, ToolMultiply
from custom_agents.math_tool.tool_divide import tool_divide_fn, ToolDivide
from custom_agents.math_tool.response import response_fn
from models.agent import Classifier, Processor, Replicator, Tool
from src.message import Message, Messages
from src.agent import Agent
from src.llm import LLM, LlmApi
from src.instructions import LlmInstructions
import logging
import numpy as np
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

class AgentBitcoinput(Classifier):
    list_of_words: list[str] = Field(
        description='lista das palavras mais prováveis'
    )

agent_bitcoin = Agent(
    name='agent_bitcoin',
    role='user:linked',
    output_schema=AgentBitcoinput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Voce é um assistente que recebe uma lista de palavras e uma frase digitada pelo usuário. Sua tarefa é encontrar as palavras da lista que têm alguma relação com a frase do usuário. ',
            steps=[
                'A frase pode contar a referência direta da palavra ou referência indireta',
                'Sempre coloque todas as palavras com alguma ligação, mesmo as com ligação indireta',
                'Coloque em ordem de relevância as palavras mais prováveis de serem a resposta',
            ],
            tools=[],
            reasoning=True,
            output_schema=AgentBitcoinput,
        ),
        debug=True,
    ),
    num_workers=1,
)

def word_list():
    with open('custom_agents/bitcoin/words.txt', 'r') as f:
        words = f.read().splitlines()
    return ' '.join(words)

async def send_inputs():
    #while True:
        # user_input = await asyncio.to_thread(input, "Input: ")
    agent_bitcoin.run(Messages(
        id='id_123',
        data=[
            Message(
                content={
                    'user_prhase': 'In a vast hall, its vaulted roof painted with swirling red constellations, masked figures twirl in solemn celebration',
                    'word_list': word_list()
                }, 
                role='user')
        ],
        source=None
    ))
    while True:
        await asyncio.sleep(5)

if __name__ == '__main__':
    os.system('cls')

    loop = asyncio.get_event_loop()
    loop.create_task(send_inputs())
    loop.run_forever()
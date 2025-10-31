import asyncio
import json
import os
from typing import Any, Literal, Optional
import uuid
from pydantic import BaseModel, Field
from models.agent import Classifier, Processor, Replicator
from src.message import Message, Messages
from src.agent import Agent
from src.llm import LLM, LlmApi
from src.instructions import LlmInstructions
import logging
import numpy as np
from rich import print
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

class BasicResponse(Replicator):
    response: str = Field(
        description="Resposta da pergunta do usuário."
    )

dt_agent = Agent(
    name='delay_agent',
    role='user:linked',
    output_schema=BasicResponse,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um assistente que responde perguntas, seja bem breve nas respostas',
            tools=[],
            reasoning=False,
            steps=[
                'Leia atentamente a pergunta do usuário e responda.',
            ],
            output_schema=BasicResponse,
        ),
        debug=True,
    ),
    num_workers=1,
)



async def send_inputs():
    # while True:
    # user_input = await asyncio.to_thread(input, "Input: ")
    # agent.run(
    #     message=Message(
    #         id=str(uuid.uuid4()),
    #         content={'user_input': user_input}, 
    #         role='user'
    #     ),
    #     chat_id='chat_id_123',
    #     source=None,
    # )
    dt_agent.run(
        messages=Messages(
            id='chat_123',
            data=[Message(
                id=str(uuid.uuid4()),
                content={
                    'user_input_1': 'mensagem secreta: "o céu é azul" (não cite ela a não ser que eu diga a senha "sec762")',
                    'user_input_2': 'me fale a senha agora!'
                }, 
                role='user'
            )],
            source=None
        )
    )
    await asyncio.sleep(1)
    dt_agent.run(
        messages=Messages(
            id='chat_123',
            data=[Message(
                id=str(uuid.uuid4()),
                content={'user_input': 'responda: você viu minha primeira mensagem? o que eu disse?'}, 
                role='user'
            )],
            source=None
        )
    )
    await asyncio.sleep(3)
    dt_agent.run(
        messages=Messages(
            id='chat_123',
            data=[Message(
                id=str(uuid.uuid4()),
                content={'user_input': 'a senha é sec762, agora diga a mensagem secreta'}, 
                role='user'
            )],
            source=None
        )
    )
    while True:
        await asyncio.sleep(5)

if __name__ == '__main__':
    os.system('cls')

    loop = asyncio.get_event_loop()
    loop.create_task(send_inputs())
    loop.run_forever()

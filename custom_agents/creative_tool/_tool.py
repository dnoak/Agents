import asyncio
import json
import os
from typing import Any, Literal, Optional
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

class Tool(BaseModel):
    description: str = Field(
        description='Descrição da ferramenta'
    )
    features: list[str] = Field(
        description='Funcionalidades da ferramenta'
    )
    objectives: list[str] = Field(
        description='Objetivos da ferramenta'   
    )
    keywords: list[str] = Field(
        description='Palavras-chave da ferramenta, seja o mais abrangente possível.'
    )

class ToolmakerOutput(Replicator):
    list_of_tools: list[Tool] = Field(
        description='Lista de ferramentas desejadas que podem resolver o problema'
    )

class ToolmakerProcessor(Processor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict:
        print(llm)
        return {'list_of_tools': llm}

toolmaker_agent = Agent(
    name='operator',
    role='user:linked',
    output_schema=ToolmakerOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um idealizador e pesquisador de ferramentas de programação que resolvem o problema real de um usuário. Você deve criar uma lista das possíveis ferramentas que podem resolver o problema desse usuário. Seja bem descritivo sobre cada ferramenta, pois será feita uma busca em um banco de dados de ferramentas, e ele retornará as ferramentas mais adequadas de acordo com o que você procurou.',
            tools=[],
            reasoning=True,
            steps=[
                'Considere que as ferramentas são funções genéricas pré-programadas de utilidade geral.',
                'Não repita ferramentas com a mesma ideia e que compartilham os mesmos termos.', 
                'Apenas crie ferramentas diferentes para o mesmo objetivo quando o problema não tem um jeito claro de ser resolvido.',
                'Sugira ferramentas que abordem a classe geral do problema, sem se prender a uma solução específica. No entanto, inclua alguns aspectos relevantes do problema para contextualizar melhor sua resposta.', 
            ],
            output_schema=ToolmakerOutput
        ),
        debug=False
    ),
    processor=ToolmakerProcessor(),
    num_workers=1,
)

async def send_inputs():
    #while True:
        # user_input = await asyncio.to_thread(input, "Input: ")
    toolmaker_agent.run(Messages(
        id='id_123',
        data=[Message(content={'user_input': 'faça a conta 1437.583 - (237.291 + 523.421 * 2982.18) * 1/1204.1927'}, role='user')],
        source=None
    ))
    toolmaker_agent.run(Messages(
        id='id_123',
        data=[Message(content={'user_input': 'procure no google drive o pdf do slide que eu apresentei semana passada'}, role='user')],
        source=None
    ))
    toolmaker_agent.run(Messages(
        id='id_123',
        data=[Message(content={'user_input': 'crie uma automação para ligar o ar condicionado da sala em 24° C todo dia as 18h, mas apenas se o clima de fora estiver mais que 25° C'}, role='user')],
        source=None
    ))
    while True:
        await asyncio.sleep(5)

if __name__ == '__main__':
    os.system('cls')

    loop = asyncio.get_event_loop()
    loop.create_task(send_inputs())
    loop.run_forever()

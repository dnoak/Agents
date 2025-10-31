import asyncio
from typing import Optional
import graphviz
from pydantic import Field, model_validator
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Replicator, Classifier, Processor

class Output0(Replicator):
    output_0: str = Field(description="Resposta")
class Output1(Replicator):
    output_1: str = Field(description="Resposta")
class OutputFormatter(Replicator):
    output_formatted: str = Field(description="Resposta formatada")

agent_0 = Agent(
    name='agent_0',
    role='user',
    output_schema=Output0,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),
        instructions=LlmInstructions(
            background='Você responde perguntas no formato JSON',
            reasoning=False,
            steps=['escreva no máximo 8 palavras'],
            output_schema=Output0
        ),
        debug=True
    ),
    num_workers=1,
)

agent_1 = Agent(
    name='agent_1',
    role='user',
    output_schema=Output1,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),
        instructions=LlmInstructions(
            background='Você responde perguntas no formato JSON',
            reasoning=False,
            steps=['escreva no máximo 8 palavras'],
            output_schema=Output1
        ),
        debug=True
    ),
    num_workers=1,
)

agent_formatter = Agent(
    name='agent_formatter',
    role='assistant',
    output_schema=OutputFormatter,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),
        instructions=LlmInstructions(
            background='Você recebe N respostas, e deverá formatar elas separando as por emojis e quebras de linha. Responda em JSON',
            reasoning=False,
            steps=[],
            output_schema=OutputFormatter
        ),
        debug=True
    ),
    num_workers=1
)

agent_0.connect(agent_formatter)
agent_1.connect(agent_formatter)


async def main():
    while True:
        await asyncio.to_thread(input, "🔵 input_1")
        agent_1.run(Message(
            id='abc123',
            content={'input': 'carros economicos?'},
            history=[],
            role='user',
            source=None
        ))

        await asyncio.to_thread(input, "🔵 input_0")
        agent_0.run(Message(
            id='abc123',
            content={'input': 'tubarao branco?'},
            history=[],
            role='user',
            source=None
        ))


        # if 'abc123' not in agent.llm.metadata:
        #     print('🟢 Nenhuma chamada para o LLM')
        #     continue
        # for cost in agent.llm.metadata['abc123']:
        #     print(cost)

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()



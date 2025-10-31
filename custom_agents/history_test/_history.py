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

class AgentClassifierOutput(Classifier):
    agent_multiply: bool = Field(
        description='Agente que faz cálculos de multiplicação'
    )
    agent_divide: bool = Field(
        description='Agente que faz cálculos de divisão'
    )

class AgentMultiplyOutput(Replicator):
    multiply_result: float | None = Field(
        default=None,
        description='Resposta final da sua tarefa.'
    )

class AgentDivideOutput(Replicator):
    divide_result: float | None = Field(
        default=None,
        description='Resposta final da sua tarefa',
    )

class AgentFormatterOutput(Replicator):
    formatted_result: str = Field(
        description='Resposta final da sua tarefa.'
    )

class AgentGeneratorOutput(Replicator):
    new_calc: str = Field(
        description='Cálculo matemático gerado, usando apenas multiplicação ou divisão.'
    )

agent_classifier = Agent(
    name='agent_classifier',
    role='user:linked',
    output_schema=AgentClassifierOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um assistente que classifica os agentes que podem resolver uma determinada tarefa.',
            tools=[],
            reasoning=True,
            steps=[
                'Leia atentamente a pergunta do usuário e identifique seu tema central.',
            ],
            output_schema=AgentClassifierOutput,
        ),
        debug=True,
    ),
    num_workers=1,
)

agent_multiply = Agent(
    name='agent_multiply',
    role='user:linked',
    output_schema=AgentMultiplyOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um assistente que faz cálculos matemáticos utilizando Tools externas. Você pode solicitar um cálculo, receber o resultado concreto e, a partir dele, fazer novos cálculos em um processo encadeado até obter o resultado final. No entanto, você não pode antecipar resultados futuros nem encadear múltiplas Tools em um único passo sem conhecer os valores intermediários. Cada Tool deve ser chamada apenas com valores numéricos concretos já disponíveis.',
            tools=[ToolMultiply],
            reasoning=True,
            steps=[
                'Leia atentamente a pergunta do usuário e identifique seu tema central.',
                'Quebre as operações em etapas, e siga a ordem de operações da matemática.',
                '**Todo** cálculo deve ser feito usando alguma [Tool].',  
            ],
            output_schema=AgentMultiplyOutput,
        ),
        debug=True,
    ),
    num_workers=1,
)

agent_divide = Agent(
    name='agent_divide',
    role='user:linked',
    output_schema=AgentDivideOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um assistente que faz cálculos matemáticos utilizando Tools externas. Você pode solicitar um cálculo, receber o resultado concreto e, a partir dele, fazer novos cálculos em um processo encadeado até obter o resultado final. No entanto, você não pode antecipar resultados futuros nem encadear múltiplas Tools em um único passo sem conhecer os valores intermediários. Cada Tool deve ser chamada apenas com valores numéricos concretos já disponíveis.',
            tools=[ToolDivide],
            reasoning=True,
            steps=[
                'Leia atentamente a pergunta do usuário e identifique seu tema central.',
                'Quebre as operações em etapas, e siga a ordem de operações da matemática.',
                '**Todo** cálculo deve ser feito usando alguma [Tool].',  
            ],
            output_schema=AgentDivideOutput,
        ),
        debug=True,
    ),
    num_workers=1,
)

agent_formatter = Agent(
    name='agent_formatter',
    role='assistant',
    output_schema=AgentFormatterOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um assistente que formata o resultado de cáculos matemáticos que foram obtidos através de outros agentes. O resultado final estará no histórico da conversa, você utilizará ele para formatar a resposta. Em seguida, você deve criar uma nova conta matemática para o usuário, use apenas soma ou subtração.',
            tools=[],
            reasoning=False,
            steps=[
                'Escreva o resultado formatado de acordo com a pergunta do usuário.',
                'Exemplo: caso a pergunta seja "qual a soma de X+Y?", você responderá "O resultado da conta {conta na pergunta do usuário} é {resultado}".', 
            ],
            output_schema=AgentFormatterOutput,
        ),
        debug=True,
    ),
    num_workers=1,
)

agent_generator = Agent(
    name='agent_generator',
    role='user',
    output_schema=AgentGeneratorOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um usuário que pede para resolver uma conta matemática. Você deve criar aleatoriamente uma conta matemática usando apenas divisão ou multiplicação.', 
            tools=[],
            reasoning=False,
            steps=[
                'Escreva apenas dois números e a operação * ou / entre eles.', 
                'Escreva a conta como se fosse uma pergunta, por exemplo: "Qual a multiplicação de 2 * 2?" ou "Qual a divisão de 5 / 3?"',
                'Você terá o histórico de conversa, use sempre o resultado da última conta como o primeiro número na criação da nova conta matemática, o segundo número você pode inventar, mas não use os resultados do histórico nele.',
                'O segundo número deve ser um número real com várias casas decimais, por exemplo: 2.345, 3.1415, 0.123456789.',
            ],
            output_schema=AgentGeneratorOutput,
        ),
        debug=True,
    ),
    num_workers=1,
)

agent_classifier.connect(agent_multiply)
agent_classifier.connect(agent_divide)

agent_multiply.connect(agent_formatter, required=False)
agent_divide.connect(agent_formatter, required=False)

agent_formatter.connect(agent_generator, required=False)
agent_generator.connect(agent_classifier, required=False)

agent_formatter.plot()

async def send_inputs():
    #while True:
        # user_input = await asyncio.to_thread(input, "Input: ")
    agent_classifier.run(Messages(
        id='id_123',
        data=[Message(content={'user_input': 'faça a conta 237.291 / 523.421'}, role='user')],
        source=None
    ))
    while True:
        await asyncio.sleep(5)

if __name__ == '__main__':
    os.system('cls')

    loop = asyncio.get_event_loop()
    loop.create_task(send_inputs())
    loop.run_forever()
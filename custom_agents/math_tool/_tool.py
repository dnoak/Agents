import asyncio
import json
import os
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from custom_agents.math_tool.tool_sum import tool_add_fn, ToolAdd
from custom_agents.math_tool.tool_subtract import tool_subtract_fn, ToolSubtract
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

class OperatorLlmOutput(Replicator):
    result: float | None = Field(
        default=None,
        description='Resposta final da sua tarefa.'
    )

class OperatorOutput(Replicator):
    result: float | None = Field(
        default=None,
        description='Resposta final da sua tarefa.'
    )

class OperatorProcessor(Processor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        if llm['_task_completion_status'] == 'success':
            isclose = np.isclose(141.135239787, llm['result'], atol=0.01)
            print(f'target: {141.135}, llm result: {round(llm["result"], 3)}')
            if isclose:
                print('🟢 task `success`, correct result:', llm['result'])
                return {'result': llm}
            print('🟡 task `success`, incorrect result:', llm['result'])
            return {'result': llm['result']}
        print('🔴 task Failed, incomplete result:', llm['result'])
        return {'result': llm['result']}

agent_operator = Agent(
    name='operator',
    role='user:linked',
    output_schema=OperatorOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini'),#, base_url='http://localhost:1234/v1'),
        instructions=LlmInstructions(
            background='Você é um assistente que faz cálculos matemáticos utilizando Tools externas. Você pode solicitar um cálculo, receber o resultado concreto e, a partir dele, fazer novos cálculos em um processo encadeado até obter o resultado final. No entanto, você não pode antecipar resultados futuros nem encadear múltiplas Tools em um único passo sem conhecer os valores intermediários. Cada Tool deve ser chamada apenas com valores numéricos concretos já disponíveis.',
            tools=[ToolAdd, ToolSubtract, ToolMultiply, ToolDivide],
            reasoning=True,
            steps=[
                'Leia atentamente a pergunta do usuário e identifique seu tema central.',
                'Quebre as operações em etapas, e siga a ordem de operações da matemática.',
                '**Todo** cálculo deve ser feito usando alguma [Tool].',
            ],
            output_schema=OperatorLlmOutput
        ),
        debug=True
    ),
    processor=OperatorProcessor(),
    num_workers=1,
)

async def send_inputs():
    #while True:
        # user_input = await asyncio.to_thread(input, "Input: ")
    agent_operator.run(Messages(
        id='id_123',
        #data=[Message(content={'user_input': 'faça a conta 1437.583 - (237.291 + 523.421 * 2982.18) * 1/1204.1927'}, role='user')],
        data=[Message(id='123', content={'user_input': 'faça a conta 1437.583 - (237.291 + 523.421 * 2982.18) * 1/1204.1927'}, role='user')],
        source=None
    ))
    while True:
        await asyncio.sleep(5)

if __name__ == '__main__':
    os.system('cls')

    loop = asyncio.get_event_loop()
    loop.create_task(send_inputs())
    loop.run_forever()

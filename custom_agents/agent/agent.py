from typing import Literal
from pydantic import BaseModel
from src.nodes.node import Node, NodeProcessor, NodeSource
from dataclasses import dataclass
import asyncio
import numpy as np
from rich import print
from litellm import acompletion
from config import settings

@dataclass
class UserInput(NodeProcessor):
    async def execute(self) -> str:
        return input('User: ')
    
class ClassifierOutput(BaseModel):
    choices: Literal['basic_response', 'pesticide_search']

@dataclass
class Classifier(NodeProcessor):
    system_prompt: str = '''Você é um agente classificador de conteúdos de agronomia. Você deve classificar a mensagem do usuário entre:
    - basic_response: o usuário fez uma pergunta genérica sobre agronomia.
    - pesticide_search: o usuário está procurando informações de pestifida.'''
    async def execute(self) -> str:
        usr =self.inputs['user_input'].result
        if 'agronomia' in usr:
            self.routing.add('basic_response')
        elif 'pesticide' in usr:
            self.routing.add('pesticide_search')
        else:
            self.routing.clear()
        # response = await acompletion(
        #     model='gpt-5-mini',
        #     messages=[{
        #         'system': self.system_prompt,
        #         'user': self.inputs['user_input'].result,
        #     }],
        #     response_format=ClassifierOutput
        # )
        # self.routing.set(response.choices[0].message.content)
        return self.inputs['user_input'].result

@dataclass
class BasicResponse(NodeProcessor):
    async def execute(self) -> str:
        return 'Basic response'
    
@dataclass
class PesticideSearch(NodeProcessor):
    async def execute(self) -> str:
        return 'Pesticide search'

async def main():
    user_input = Node(name="user_input", processor=UserInput())
    classifier = Node(name="classifier", processor=Classifier())
    basic_response = Node(name="basic_response", processor=BasicResponse())
    pesticide_search = Node(name="pesticide_search", processor=PesticideSearch())

    user_input.connect(classifier)
    classifier.connect(basic_response)
    classifier.connect(pesticide_search)
    classifier.plot()

    res = await user_input.run(
        input=None,
        execution_id='exec_1',
        source=NodeSource(id='user_1', node=None),
    )
    print(res)

asyncio.run(main())
import asyncio
import random
from typing import Literal
import uuid
from nodesIO.engine.node import Node
from nodesIO.models.node import NodeExecutorConfig, NodeIO, NodeIOStatus, NodeIOSource
from dataclasses import dataclass
from rich import print

@dataclass
class LLM:
    async def argue(self, question: str, stance: str) -> str:
        return f'🤔 I am {stance}, and I argue that {question}'
    
    async def respond(self, stance: str, argument: str) -> str:
        return f'🤝 I am {stance}, and I respond with {argument}'
    

@dataclass
class Entry(Node):
    async def execute(self, ctx) -> str:
        question = ctx.inputs.outputs[0]
        ctx.routing.clear()
        if random.choice([True, False]): # 50/50 chance
            ctx.routing.add('defensor')
        else:
            ctx.routing.add('acuser')
        return question

@dataclass
class Defensor(Node):
    stance: str

    async def execute(self, ctx) -> dict[str, str]:
        question = ctx.inputs['entry'].output
        argument = await llm.argue(question, stance=self.stance)
        return {'stance': self.stance, 'argument': argument}

@dataclass
class Accuser(Node):
    stance: str

    async def execute(self, ctx) -> dict[str, str]:
        question = ctx.inputs['entry'].output
        argument = await llm.argue(question, stance=self.stance)
        return {'stance': self.stance, 'argument': argument}

@dataclass
class Response(Node):
    async def execute(self, ctx) -> str:
        stance = ctx.inputs.outputs[0]['stance']
        argument = ctx.inputs.outputs[0]['argument']
        return await llm.respond(stance, argument)
    

entry = Entry(name='entry')
defensor = Defensor(name='defensor', stance='defensor')
acuser = Accuser(name='acuser', stance='acuser')
response = Response(name='response')

entry.connect(defensor)
entry.connect(acuser)
defensor.connect(response)
acuser.connect(response)

# entry.plot()

llm = LLM()

async def main():
    for question in ['What is the meaning of life?', 'Why is the sky blue?']:
        result = await entry.run(NodeIO(
            source=NodeIOSource(
                session_id='session_1', 
                execution_id=str(uuid.uuid4()), 
                node=None
            ),
            status=NodeIOStatus(),
            output=question,
        ))
        print(f'{result}')
asyncio.run(main())

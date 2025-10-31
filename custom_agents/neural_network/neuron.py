from dataclasses import dataclass
import numpy as np
from pydantic import BaseModel, Field
from src.agent import Agent
from src.message import Message, Messages
from models.agent import Processor, Replicator

class NeuronOutput(Replicator):
    a: float = Field(
        description="Saída do neurônio artificial"
    )

@dataclass
class NeuronProcessor(Processor):
    w: list[float]
    b: float

    def process(self, agent: Agent, messages: list[Messages], llm: dict) -> dict | None:
        w = np.array(self.w)
        z = np.sum(w * np.array([m.last.content['a'] for m in messages])) + self.b
        a = 0 if z < 0 else z
        print(a)
        # time.sleep(0.5)
        return {'a': a}

def neuron_fn(name: str, w: list[float], b: float, debug: dict = {'output': False, 'llm': False}):
    return Agent(
        name=name,
        role='user:linked',
        output_schema=NeuronOutput,
        processor=NeuronProcessor(w=w, b=b),
        num_workers=1,
    )
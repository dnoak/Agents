import asyncio
from dataclasses import dataclass
import os
import random
import time
from timeit import default_timer
from fastapi import FastAPI
import numpy as np
from pydantic import BaseModel, Field
from src.agent import Agent
from src.message import Message, Messages
from models.agent import Processor, Replicator
from custom_agents.neural_network.neuron import neuron_fn
import random

def b():
    return random.random()

def w(size: int):
    return [random.random() for _ in range(size)]

network = [
    [neuron_fn('x', [1], 0), neuron_fn('y', [1], 0), neuron_fn('z', [1], 0)],
    [neuron_fn(f'agent_neuron_L0_{i}', w(3), b()) for i in range(5)],
    [neuron_fn(f'agent_neuron_L1_{i}', w(5), b()) for i in range(5)],
    [neuron_fn(f'agent_neuron_L2_{i}', w(5), b()) for i in range(5)],
    [neuron_fn(f'agent_neuron_L3_{i}', w(5), b()) for i in range(5)],
    [neuron_fn(f'agent_neuron_L4_{i}', w(5), b()) for i in range(1)],
]

for layer, next_layer in zip(network, network[1:]):
    for neuron in layer:
        for next_neuron in next_layer:
            neuron.connect(next_neuron)

# animation_started = False

network[0][0].plot()

class InputMessage(BaseModel):
    id: str
    xyz: list[float]

    class Config:
        json_schema_extra = {
            "examples": [
                {"id": "user_1", "xyz": [1, 2, 3]},
            ]
        }

async def send_inputs():
    # global animation_started
    # user_input = await asyncio.to_thread(input, "Input: ")
    while True:
        id = str(random.randint(0, 100000))
        xyz = [random.random() for _ in range(3)]
        for input_neuron, value, in zip(network[0], xyz):
            input_neuron.run(Messages(
                id=id,
                data=[Message(content={'a': value}, role='user')],
                source=None
            ))
        # if not animation_started:
        #     network[0][0].plot(animate=True)
        #     animation_started = True
        await asyncio.sleep(2)
    



loop = asyncio.get_event_loop()
loop.create_task(send_inputs())
loop.run_forever()
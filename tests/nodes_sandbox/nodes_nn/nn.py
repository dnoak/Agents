import random
from src.models.node import NodeOutputFlags
from src.nodes.node import Node, NodeProcessor, NodeSource
from dataclasses import dataclass
import asyncio
import numpy as np
from rich import print
from config import settings

@dataclass
class NeuronInput(NodeProcessor):
    async def execute(self) -> float:
        # print(f'{self.inputs._inputs[0].execution_id} {self.node.name}: {self.inputs.results} {self.inputs[settings.node.first_execution_source].result}')
        return self.inputs[settings.node.first_execution_source].result

@dataclass
class Neuron(NodeProcessor):
    w: list[float]
    b: float
    
    async def execute(self) -> float:
        # print(f"{self.node.name}: {self.inputs.results}")
        x = np.array(self.inputs.results)
        z = x @ self.w + self.b
        a = max(z, 0.)
        return float(a)
    
def neuron(x: float, y: float) -> float:
    a1 = np.array([[x, y]]) @ np.array([[-0.69, -0.77], [-0.26, +0.97], [+0.95, -0.19]]).T + np.array([-0.23, -0.29, -0.27])
    a1[a1 < 0] = 0.

    a2 = a1 @ np.array([0.93, 0.99, 0.93]) + np.array([-1.4])
    a2[a2 < 0] = 0.

    a3 = a2 @ np.array([-1]) + np.array([1])
    a3[a3 < 0] = 0.

    return a3
    

async def nn():
    nx = Node(name="nx", processor=NeuronInput())
    ny = Node(name="ny", processor=NeuronInput())
    
    n11 = Node(name="n11", processor=Neuron(w=[-0.69, -0.77], b=-0.23))
    n12 = Node(name="n12", processor=Neuron(w=[-0.26, +0.97], b=-0.29))
    n13 = Node(name="n13", processor=Neuron(w=[+0.95, -0.19], b=-0.27))

    n21 = Node(name="n21", processor=Neuron(w=[0.93, 0.99, 0.93], b=-1.4))
    n31 = Node(name="n31", processor=Neuron(w=[-1], b=1))

    nx.connect(n11)
    nx.connect(n12)
    nx.connect(n13)
    ny.connect(n11)
    ny.connect(n12)
    ny.connect(n13)

    n11.connect(n21)
    n12.connect(n21)
    n13.connect(n21)
    
    n21.connect(n31)
    

    outputs = []
    real_outputs = []
    for i in range(200):
        rx = random.uniform(-4, 4)
        ry = random.uniform(-4, 4)
        inputs = [
            nx.run(
                input=rx,
                execution_id=f'id{i}',
                source=NodeSource(id=f'user_nn{i}', node=None),
                flags=NodeOutputFlags(),
            ),
            ny.run(
                input=ry,
                execution_id=f'id{i}',
                source=NodeSource(id=f'user_nn{i}', node=None),
                flags=NodeOutputFlags(),
            ),
        ]
        outputs.append(sum(await asyncio.gather(*inputs), []))
        real_outputs.append(neuron(rx, ry))

    # random.shuffle(inputs)

    # res = sum(await asyncio.gather(*inputs), [])
    # print(res)

    for o, r in zip(outputs, real_outputs):
        assert o[0].result == r[0]
        print(o[0].result, r[0])

    # print(nx.executions.get('id0'))

    # print(nx.inputs_queue.pending, nx.inputs_queue.futures)
    # print(ny.inputs_queue.pending, ny.inputs_queue.futures)
    # print(n11.inputs_queue.pending, n11.inputs_queue.futures)
    # print(n12.inputs_queue.pending, n12.inputs_queue.futures)
    # print(n13.inputs_queue.pending, n13.inputs_queue.futures)
    # print(n21.inputs_queue.pending, n21.inputs_queue.futures)
    # print(n31.inputs_queue.pending, n31.inputs_queue.futures)
    

asyncio.run(nn())
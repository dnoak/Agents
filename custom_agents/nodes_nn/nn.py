from src.node import Node, NodeProcessor, NodeSource
from dataclasses import dataclass
import asyncio
import numpy as np
from rich import print
    
@dataclass
class NeuronInput(NodeProcessor):
    async def execute(self) -> float:
        return self.inputs['__start__'].result

@dataclass
class Neuron(NodeProcessor):
    w: list[float]
    b: float
    
    async def execute(self) -> float:
        x = np.array(self.inputs.results)
        z = x @ self.w + self.b
        a = max(z, 0.)
        return float(a)

async def nn():
    nx = Node(name="nx", processor=NeuronInput(),)
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
    # n11.plot()

    inputs = [
        nx.run(
            input=1.9,
            execution_id='nn',
            source=NodeSource(id='user_nn', node=None),
        ),
        ny.run(
            input=-0.9,
            execution_id='nn',
            source=NodeSource(id='user_nn', node=None),
        ),
    ]

    res = sum(await asyncio.gather(*inputs), [])
    print(res)

asyncio.run(nn())
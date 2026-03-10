import asyncio
from nodesIO.engine.node import Node
from nodesIO.models.node import NodeIO, NodeIOStatus, NodeIOSource
from dataclasses import dataclass
import numpy as np
from rich import print

@dataclass
class Neuron(Node):
    w: list[float]
    b: float

    async def execute(self, ctx) -> float:
        x = np.array(ctx.inputs.outputs)
        z = x @ self.w + self.b
        a = max(z, 0.)
        return float(a)

n1 = Neuron(name="n1", w=[1], b=0)
n2 = Neuron(name="n2", w=[2], b=0)
n3 = Neuron(name="n3", w=[3], b=0)
n4 = Neuron(name="n4", w=[4, 5], b=0)

n1.connect(n2)
n1.connect(n3)
n2.connect(n4)
n3.connect(n4)

async def main():
    result = await n1.run(
        NodeIO(
            source=NodeIOSource(
                session_id='session_1', 
                execution_id='exec_1', 
                node=None
            ),
            status=NodeIOStatus(),
            output=1,
        )
    )
    print(result)

asyncio.run(main())
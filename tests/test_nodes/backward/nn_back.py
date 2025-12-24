import random
import uuid
from nodesio.engine.node import Node
from nodesio.models.node import (
    NodeExternalInput,
    NodeExecutorConfig,
    NodeIO, 
    NodeIOStatus, 
    NodeIOSource,
)
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print

@dataclass
class NeuronInput(Node):
    async def execute(self) -> float:
        return self.inputs[NodeExternalInput].result

@dataclass
class Alphabet(Node):
    w: np.ndarray = field(init=False)
    b: float = field(init=False)

    def compile_wandb(self):
        if not len(self._input_nodes):
            size = 1
        else:
            size = len(self._input_nodes)
        self.w = np.random.random(size=size)
        self.b = np.random.random()

    def backward(self):
        self._input_nodes, self._output_nodes = self._output_nodes, self._input_nodes

    async def execute(self) -> float:
        x = np.array(self.inputs.results)
        print(f'{self.name} {len(self.node._input_nodes)}, {x}, {self.w}')
        z = x @ self.w + self.b
        a = max(z, 0.)
        return float(a)

a = Alphabet(name='a')
b = Alphabet(name='b')
c = Alphabet(name='c')
d = Alphabet(name='d')
e = Alphabet(name='e')
f = Alphabet(name='f')
g = Alphabet(name='g')


a.connect(b)
a.connect(c)
b.connect(d)
c.connect(d)
d.connect(e)
e.connect(f)
d.connect(g)
f.connect(g)
a.plot()

async def main(backward: bool = False):
    if backward:
        first_node = g
    else:
        first_node = a
    res = await first_node.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4())[:4], node=None),
        result=[1],
        status=NodeIOStatus(),
    ))
    print(res)

for node in [a, b, c, d, e, f, g]:
    node.compile_wandb()

asyncio.run(main())

for node in [a, b, c, d, e, f, g]:
    node.backward()
    node.compile_wandb()

asyncio.run(main(backward=True))

# a.plot()

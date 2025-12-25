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
class Neuron(Node):
    w: np.ndarray = field(init=False)
    b: float = field(init=False)
    w_grad: np.ndarray = field(init=False)
    b_grad: float = field(init=False)
    backward_mode: bool = False
    x: np.ndarray = field(init=False)
    z: np.ndarray = field(init=False)
    a: np.ndarray = field(init=False)
    lr: float = 0.1

    def init_wandb(self):
        self.w = np.random.random(size=max(len(self._input_nodes), 1))
        self.b = np.random.random()
        self.w_grad = np.zeros_like(self.w)
        self.b_grad = 0
        self.x = np.zeros(self.w.shape)
        self.z = np.zeros(1)
        self.a = np.zeros(1)

    def toggle_backward_mode(self):
        self._input_nodes, self._output_nodes = self._output_nodes, self._input_nodes

    def grad(self):
        self.w -= self.w_grad * self.lr
        self.b -= self.b_grad * self.lr

    def zero_grad(self):
        self.w_grad *= 0
        self.b_grad *= 0
    
    def backward(self) -> np.ndarray:
        delta = np.sum(self.inputs.results)
        # print('🔴', self.x, self.z, self.a)
        dadz = 1 if self.z[0] > 0 else 0 
        dzdw = self.x
        dzdb = 1
        # print(f'dadz: {dadz}')
        # print(f'dzdw: {dzdw}')
        # print(f'dzdb: {dzdb}')
        # print(f'delta: {delta}')
        # print(f'w_grad: {self.w_grad}')
        # print(f'b_grad: {self.b_grad}')

        self.w_grad += delta * dadz * dzdw
        self.b_grad += delta * dadz * dzdb
        # print(f'w_grad: {self.w_grad}')
        # print(f'b_grad: {self.b_grad}')
        delta = delta * dadz * dzdw 
        return delta

    def forward(self) -> np.ndarray:
        self.x = np.array(self.inputs.results).T
        self.z = self.x @ self.w + self.b
        self.a = self.z[self.z > 0]
        # print(self.x, self.z, self.a)
        return self.a

    async def execute(self) -> np.ndarray:
        if not self.backward_mode:
            return self.forward()
        return self.backward()

a = Neuron(name='a')
b = Neuron(name='b')
c = Neuron(name='c')
d = Neuron(name='d')
e = Neuron(name='e')
f = Neuron(name='f')
g = Neuron(name='g')


a.connect(b)
a.connect(c)
b.connect(d)
c.connect(d)
d.connect(e)
d.connect(f)
f.connect(g)
e.connect(g)
# a.plot()


async def train_step():
    output = await a.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4())[:4], node=None),
        result=[1],
        status=NodeIOStatus(),
    ))
    print(output[0].result)

    for node in [a, b, c, d, e, f, g]:
        node.toggle_backward_mode()
        node.backward_mode = True
    
    await g.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4())[:4], node=None),
        result=[2],
        status=NodeIOStatus(),
    ))
    for node in [a, b, c, d, e, f, g]:
        node.grad()
        node.zero_grad()
        node.backward_mode = False
        node.toggle_backward_mode()
    
    output = await a.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4())[:4], node=None),
        result=[1],
        status=NodeIOStatus(),
    ))
    print(output[0].result)
    

for node in [a, b, c, d, e, f, g]:
    node.init_wandb()


asyncio.run(train_step())


# a.plot()

import random
from typing import Any
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
    lr: float = 0.01
    w: np.ndarray = field(init=False)
    b: float = field(init=False)
    w_grad: np.ndarray = field(init=False)
    b_grad: float = field(init=False)
    x: np.ndarray = field(init=False)
    z: np.ndarray = field(init=False)
    a: np.ndarray = field(init=False)

    def init_wandb(self):
        self.w = 2*(np.random.random(size=max(len(self._input_nodes), 1)) - 1/2)
        self.b = 2*(np.random.random() - 1/2)
        self.w_grad = np.zeros_like(self.w)
        self.b_grad = 0
        self.x = np.zeros(self.w.shape)
        self.z = np.zeros(1)
        self.a = np.zeros(1)

    def toggle_backward_mode(self):
        self._input_nodes, self._output_nodes = self._output_nodes, self._input_nodes

    def apply_grads(self):
        self.w -= self.w_grad * self.lr
        self.b -= self.b_grad * self.lr

    def zero_grads(self):
        self.w_grad *= 0
        self.b_grad *= 0
    
    def backward(self, inputs: list[float]) -> np.ndarray:
        delta = np.sum(inputs)
        dadz = 1 if self.z[0] > 0 else 0 
        dzdw = self.w.squeeze()
        dzdb = 1
        # print(f'dadz: {dadz}')
        # print(f'dzdw: {dzdw}')
        # print(f'dzdb: {dzdb}')
        # print(f'delta: {delta}')
        # print(f'w_grad: {self.w_grad}')
        # print(f'b_grad: {self.b_grad}')

        # print(f'w_grad: {self.w_grad}')
        # print(f'b_grad: {self.b_grad}')
        # print(f'delta: {delta}')
        # print(f'dadz: {dadz}')
        # print(f'dzdw: {dzdw}\n')

        self.w_grad += delta * dadz * dzdw
        self.b_grad += delta * dadz * dzdb
        # print(f'w_grad: {self.w_grad}')
        # print(f'b_grad: {self.b_grad}')
        delta = delta * dadz * dzdw
        return delta

    def forward(self, inputs: list[float]) -> np.ndarray:
        # self.x = np.array(self.inputs.results).T
        self.x = np.array(inputs).T
        self.z = self.x @ self.w + self.b
        self.a = np.maximum(self.z, 0)
        # print(self.x, self.z, self.a)
        # print(self.x, self.z, self.a)
        return self.a

    async def execute(self) -> tuple[str, Any]:
        mode = self.inputs.results[0][0]
        if mode == 'init_wandb':
            self.init_wandb()
            return ('init_wandb', None)
        if mode == 'toggle_backward_mode':
            self.toggle_backward_mode()
            return ('toggle_backward_mode', None)
        elif mode == 'apply_grads':
            self.apply_grads()
            self.zero_grads()
            return ('apply_grads', None)
        
        values = [r[1] for r in self.inputs.results]
        if mode == 'forward':
            return ('forward', self.forward(values))
        elif mode == 'backward':
            return ('backward', self.backward(values))
        else:
            raise ValueError(f'Invalid mode `{mode}`')

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

def init_wandb():
    for node in [a, b, c, d, e, f, g]:
        node.init_wandb()

async def toggle_backward_mode():
    for node in [a, b, c, d, e, f, g]:
        node.toggle_backward_mode()

async def apply_grads():
    return await a.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4())[:5], node=None),
        result=('apply_grads', None),
        status=NodeIOStatus(),
    ))

async def forward(inputs: list[float]):
    return await a.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4())[:5], node=None),
        result=('forward', inputs),
        status=NodeIOStatus(),
    ))

async def backward(inputs: list[float]):
    return await g.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4())[:5], node=None),
        result=('backward', inputs),
        status=NodeIOStatus(),
    ))

def loss(output: float, real_output: float) -> float:
    return (output - real_output) ** 2

async def train_step(x: float, y: float):
    forward_1 = await forward([x])
    dL = (forward_1[0].result[1] - y)
    print(f'f1: {forward_1[0].result[1]}, dL: {dL}')

    await toggle_backward_mode()
    await backward([dL])
    await toggle_backward_mode()
    await apply_grads()

    forward_2 = await forward([x])

    # print(forward_1[0].result)
    # print(forward_2[0].result)
    print(f'Loss: {loss(forward_2[0].result[1], y)}, x: {x}, y: {forward_2[0].result[1]}')
    input()

# for node in [a, b, c, d, e, f, g]:
#     node.init_wandb()


data = [(i, 2*i) for i in np.arange(100)]
init_wandb()

for epoch in range(10):
    random.shuffle(data)
    for x, y in data:
        asyncio.run(train_step(x, y))


# a.plot()

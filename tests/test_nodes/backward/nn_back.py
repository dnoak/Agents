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
        # print('🔴 applying grads for', self.name)
        self.w -= self.w_grad * self.lr
        self.b -= self.b_grad * self.lr

    def zero_grads(self):
        self.w_grad *= 0
        self.b_grad *= 0

    def backward(self, inputs: list[float]) -> np.ndarray:
        print('🔴 backward for', self.name)
        print(f'inputs: {inputs}')
        delta = np.sum(inputs) # dL/da (Gradiente vindo da frente)
        dadz = 1 if self.z[0] > 0 else 0 # Derivada da ReLU
        
        # O gradiente local (dL/dz)
        local_grad = delta * dadz
        
        # 1. Atualização dos Pesos (dL/dw = dL/dz * dz/dw)
        # dz/dw é a entrada X, não o peso W
        # print(local_grad, self.x)
        self.w_grad += local_grad * self.x[0] 
        self.b_grad += local_grad * 1
        
        # 2. Retorno para o nó anterior (dL/dx = dL/dz * dz/dx)
        # dz/dx é o peso W
        return local_grad * self.w

    def forward(self, inputs: list[float]) -> np.ndarray:
        # self.x = np.array(self.inputs.results).T
        self.x = np.array(inputs).T
        self.z = self.x @ self.w + self.b
        self.a = np.maximum(self.z, 0)
        # print(self.x, self.z, self.a)
        # print(self.x, self.z, self.a)
        return self.a

    async def execute(self, ctx) -> tuple[str, Any]:
        mode = ctx.inputs.results[0][0]
        if mode == 'init_wandb':
            self.init_wandb()
            return ('init_wandb', None)
        
        elif mode == 'toggle_backward_mode':
            self.toggle_backward_mode()
            return ('toggle_backward_mode', None)
        
        elif mode == 'apply_grads':
            self.apply_grads()
            return ('apply_grads', None)
        
        elif mode == 'zero_grads':
            self.zero_grads()
            return ('zero_grads', None)
        
        elif mode == 'forward':
            return ('forward', self.forward([r[1] for r in ctx.inputs.results]))
        
        elif mode == 'backward':
            print(f'{self.name} 🔴 backward routing ', list(ctx.routing.choices.keys()))
            return ('backward', self.backward([r[1] for r in ctx.inputs.results]))
        
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
b.connect(c)
# b.connect(d)
# c.connect(d)
# d.connect(e)
# d.connect(f)
# f.connect(g)
# e.connect(g)
# a.plot()

def init_wandb():
    for node in [a, b, c, d, e, f, g]:
    # for node in a._workflow['s1'].nodes.values():
        node.init_wandb()

def toggle_backward_mode():
    for node in a._workflow['s1'].nodes.values():
        node.toggle_backward_mode()

async def run(node: Node, mode: str, inputs = None):
    return await node.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4()), node=None),
        result=(mode, inputs),
        status=NodeIOStatus(),
    ))

def loss(output: float, real_output: float) -> float:
    return (output - real_output) ** 2

async def train_step(data):
    init_wandb()

    for epoch in range(10):
        random.shuffle(data)
        for x, y in data:     
            forward_1 = await run(a, 'forward', [x])
            dL = (forward_1[0].result[1] - y)
            print(f'foward: {forward_1[0].result[1]}, dL: {dL}')
# 
            toggle_backward_mode()
            await run(c, 'backward', [dL])
            toggle_backward_mode()

            await run(a, 'apply_grads')
            await run(a, 'zero_grads')
            for node in a._workflow['s1'].nodes.values():
                assert all(node.w_grad == 0), f'w_grad: {node.w_grad}'
                assert node.b_grad == 0, f'b_grad: {node.b_grad}'
                
            forward_2 = await run(a, 'forward', [x])

            # print(forward_1[0].result)
            # print(forward_2[0].result)
            print(f'Loss: {loss(forward_2[0].result[1], y)}, x: {x}, y: {forward_2[0].result[1]}')
            input()


data = [(i, 2*i) for i in np.arange(100)]

asyncio.run(train_step(data))


# a.plot()

from abc import ABC, abstractmethod
import random
from typing import Any, Callable
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
import matplotlib.pyplot as plt

@dataclass
class ActivationFunction(ABC):
    @abstractmethod
    def forward(self, z) -> Any: ...
    @abstractmethod
    def backward(self, z) -> Any: ...

@dataclass
class Linear(ActivationFunction):
    def forward(self, z):
        return z
    
    def backward(self, z):
        return 1

@dataclass
class ReLU(ActivationFunction):
    def forward(self, z):
        return np.maximum(z, 0)
    
    def backward(self, z):
        return 1 if z > 0 else 0

@dataclass
class Neuron(Node):
    activation: ActivationFunction
    lr: float = 0.00001
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
        self.w_grad = np.zeros_like(self.w)
        self.b_grad = 0

    def backward(self, inputs: list[float]) -> np.ndarray:
        delta: float = sum(np.sum(input) for input in inputs)
        dadz = self.activation.backward(self.z[0])
        local_grad = delta * dadz
        self.w_grad += local_grad * self.x[0] 
        self.b_grad += local_grad * 1
        return local_grad * self.w

    def forward(self, inputs: list[float]) -> np.ndarray:
        self.x = np.array(inputs).T
        self.z = self.x @ self.w + self.b
        self.a = self.activation.forward(self.z)
        return self.a

    async def execute(self, ctx) -> tuple[str, Any]:
        mode = ctx.inputs.results[0][0]
        if mode == 'apply_grads':
            self.apply_grads()
            return ('apply_grads', None)
        elif mode == 'zero_grads':
            self.zero_grads()
            return ('zero_grads', None)
        elif mode == 'forward':
            return ('forward', self.forward([r[1] for r in ctx.inputs.results]))
        elif mode == 'backward':
            return ('backward', self.backward([r[1] for r in ctx.inputs.results]))
        else:
            raise ValueError(f'Invalid mode `{mode}`')

a = Neuron(name='a', activation=ReLU())
b = Neuron(name='b', activation=ReLU())
c = Neuron(name='c', activation=ReLU())
d = Neuron(name='d', activation=ReLU())
e = Neuron(name='e', activation=Linear())
# f = Neuron(name='f', activation=ReLU())
# g = Neuron(name='g', activation=ReLU())

a.connect(b)
a.connect(c)
a.connect(d)
# a.connect(e)
# a.connect(f)
b.connect(e)
c.connect(e)
d.connect(e)
# e.connect(g)
# f.connect(g)
# c.connect(d)
# c.connect(d)
# d.connect(e)
# d.connect(f)
# f.connect(g)
# e.connect(g)
# a.plot()

a.init_wandb()
b.init_wandb()
c.init_wandb()
d.init_wandb()
e.init_wandb()
# f.init_wandb()
# g.init_wandb()


def toggle_backward_mode():
    for node in a._workflow['s1'].nodes.values():
        node.toggle_backward_mode()

async def run(node: Node, mode: str, inputs = None):
    return await node.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=str(uuid.uuid4()), node=None),
        result=(mode, inputs),
        status=NodeIOStatus(),
    ))

async def plot_async(node_input, data, pause=0.01):
    x_vals = np.array([d[0] for d in data])
    y_real = np.array([d[1] for d in data])
    y_pred = []
    for x in x_vals:
        res = await run(node_input, 'forward', [x])
        y_pred.append(res[0].result[1])
    y_pred = np.array(y_pred)
    ax.clear()
    ax.scatter(x_vals, y_real, color='blue', label='Real', alpha=0.5)
    ax.scatter(x_vals, y_pred, color='red', label='Predição NN', s=5, marker='o')
    ax.set_title("Treinamento em Tempo Real")
    ax.set_xlabel("Input (x)")
    ax.set_ylabel("Output (y)")
    ax.legend()
    plt.draw()
    plt.pause(pause)

def loss(output: float, real_output: float) -> float:
    return (output - real_output) ** 2

async def train_step(data):
    for epoch in range(1000):
        random.shuffle(data)
        for x, y in data:

            forward_1 = await run(a, 'forward', [x])

            dL = (forward_1[0].result[1] - y)
            toggle_backward_mode()
            await run(e, 'backward', [dL])
            toggle_backward_mode()

        await run(a, 'apply_grads')
        await run(a, 'zero_grads')

        print(f'Epoch: {epoch}, loss: {loss(forward_1[0].result[1], y)}')
        if epoch % 10 == 0:
            await plot_async(a, data)
    
    for x, y in data:
        y_pred = (await run(a, 'forward', [x]))[0].result[1]
        print(f'x: {x}, y: {y}, y_pred: {y_pred}')
    
    await plot_async(a, data, pause=0)

def circle(samples, r):
    x1_x2 = (np.random.random((samples))-1/2)
    x1_x2[:, 0] = np.cos(x1_x2[:, 0])
    x1_x2[:, 1] = np.sin(x1_x2[:, 1])
    print(x1_x2)
    y = np.array([[1] if x**2 + y**2 < r**2 else [0] for x, y in x1_x2])
    return x1_x2.astype(self.dtype), y.astype(self.dtype)

plt.ion() # Liga o modo interativo
fig, ax = plt.subplots()

data = [(i, 10*i) for i in np.arange(0, 10, 0.1)]
# data = circle(None, 1000, 1)

asyncio.run(train_step(data))


# a.plot()

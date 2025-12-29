from abc import ABC, abstractmethod
import random
import time
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
import matplotlib.patches as mpatches
from itertools import batched

@dataclass
class ActivationFunction:
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
class NeuronInput(Node):
    def toggle_backward_mode(self):
        self._input_nodes, self._output_nodes = self._output_nodes, self._input_nodes

    async def execute(self, ctx) -> list:
        return ctx.inputs.results[0]

@dataclass
class Neuron(Node):
    w: np.ndarray
    b: float
    lr: float
    activation: ActivationFunction
    w_grad: np.ndarray = field(init=False)
    b_grad: float = field(init=False)
    x: np.ndarray = field(init=False)
    z: np.ndarray = field(init=False)
    a: np.ndarray = field(init=False)

    def __post_init__(self):
        super().__post_init__()
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
        
def mlp_generator(architecture: list[tuple[int, ActivationFunction]], lr: float) -> list[list[Neuron] | list[NeuronInput]]:
    inputs = [
        NeuronInput(name=f"input_{i}")
        for i in range(architecture[0][0])
    ]
    
    layers: list[list[Neuron] | list[NeuronInput]] = [inputs]
    for layer_index, (layer_size, activation) in enumerate(architecture[1:]):
        layer = []
        for neuron_index in range(layer_size):
            layer.append(Neuron(
                name=f"L{layer_index}_N{neuron_index}", 
                w=2*(np.random.rand(architecture[layer_index][0])-1/2),
                b=2*(np.random.rand() - 1/2),
                lr=lr,
                activation=activation
            ))
        layers.append(layer)

    for layer in layers:
        for neuron in layer:
            if isinstance(neuron, NeuronInput):
                continue
    
    for current_layer, next_layer in zip(layers, layers[1:]):
        for current_neuron in current_layer:
            for next_neuron in next_layer:
                current_neuron.connect(next_neuron)
    return layers

def toggle_backward_mode(nn: list[list[Neuron] | list[NeuronInput]]):
    for node in nn[0][0]._workflow['s1'].nodes.values():
        node.toggle_backward_mode()

def plot_circle(xy_data, y_pred, acc_loss, pause):
    X = np.array([xy for (xy, _) in xy_data])
    y_true = np.array([y for (_, y) in xy_data])
    y_pred = np.array(y_pred)

    y_hat = (y_pred >= 0.5).astype(int)

    TP = X[(y_true == 1) & (y_hat == 1)]
    TN = X[(y_true == 0) & (y_hat == 0)]
    ERR = X[y_true != y_hat]

    sc_tp.set_offsets(TP)
    sc_tn.set_offsets(TN)
    sc_err.set_offsets(ERR)

    # loss_x.append(list(range(len(acc_loss))))
    # loss_y.append(loss)

    line_loss.set_data(list(range(len(acc_loss))), acc_loss)

    ax_loss.relim()
    ax_loss.autoscale_view()

    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    plt.pause(pause)


def L2(output: float, real_output: float) -> float:
    return (output - real_output) ** 2

async def run(exec_id: str, node: Node, mode: str, inputs = None):
    return await node.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=exec_id, node=None),
        result=(mode, inputs),
        status=NodeIOStatus(),
    ))

async def train_step(nn: list[list[Neuron] | list[NeuronInput]], xy_data):
    mini_batch_size = int(len(xy_data) * 0.1)
    train_loss = []
    for epoch in range(100):
        random.shuffle(xy_data)
        
        batch_loss = []
        y_pred = []
        
        for mini_batch in batched(xy_data, mini_batch_size):
            for xn, y in mini_batch:
                y_pred.append(sum(await asyncio.gather(*[
                    run(str(epoch), input_neuron, 'forward', [x])
                    for input_neuron, x in zip(nn[0], xn)
                ]), [])[0].result[1][0])
                dL = (y_pred[-1] - y)
                toggle_backward_mode(nn)
                await run(str(epoch), nn[-1][0], 'backward', [dL])
                toggle_backward_mode(nn)

                batch_loss.append(L2(y_pred[-1], y))
                
            toggle_backward_mode(nn)
            await run(str(epoch), nn[-1][0], 'apply_grads')
            await run(str(epoch), nn[-1][0], 'zero_grads')
            toggle_backward_mode(nn)

        train_loss.append(np.mean(batch_loss))
        print(f'Epoch: {epoch}, loss: {train_loss[-1]:.2f}, x: ({xn[0]:.2f}, {xn[1]:.2f}), y: {y}, y_pred: {y_pred[-1]:.2f}')

        if epoch % 1 == 0:
            plot_circle(xy_data, y_pred, train_loss, pause=0.001)
    
    plot_circle(xy_data, y_pred, train_loss, pause=0)

def circle(samples, r, square_size):
    x1_x2 = square_size*2*(np.random.random((samples, 2)) - 1/2)
    y_real = np.array([1 if (x**2 + y**2) < r**2 else 0 for x, y in x1_x2]).tolist()
    return [((x1, x2), y) for (x1, x2), y in zip(x1_x2, y_real)]


plt.ion()
fig, (ax_circle, ax_loss) = plt.subplots(1, 2, figsize=(12, 6))

sc_tp = ax_circle.scatter([], [], alpha=0.6, label="TP", color='green')
sc_tn = ax_circle.scatter([], [], alpha=0.6, label="TN", color='blue')
sc_err = ax_circle.scatter([], [], alpha=0.6, label="FN | FP", color='red')
ax_circle.set_xlim(-10, 10)
ax_circle.set_ylim(-10, 10)
ax_circle.set_title("Treinamento em Tempo Real")
ax_circle.legend(loc='upper right')

line_loss, = ax_loss.plot([], [], lw=2)
ax_loss.set_title("Loss")
ax_loss.set_xlabel("Época")
ax_loss.set_ylabel("Loss")
ax_loss.grid(True)
# ax_loss.set_xlim(0, 100)
# ax_loss.set_ylim(0, 1)

nn = mlp_generator(
    architecture=[
        (2, ReLU()), 
        (3, ReLU()), 
        (2, ReLU()), 
        (1, ReLU())
    ],
    lr=0.001
)
xy_data = circle(500, 7, 10)

asyncio.run(train_step(nn, xy_data))


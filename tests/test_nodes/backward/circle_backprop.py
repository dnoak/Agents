from abc import ABC, abstractmethod
import random
from typing import Any
from nodesIO.engine.node import Node
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print
import matplotlib.pyplot as plt
from itertools import batched
from matplotlib.colors import LinearSegmentedColormap
from scipy.interpolate import griddata
from nodesIO.models.node import (
    NodeExecutorConfig,
    NodeIO, 
    NodeIOStatus, 
    NodeIOSource,
)

@dataclass
class NeuronInput(Node):
    def toggle_train_mode(self):
        self._input_nodes, self._output_nodes = self._output_nodes, self._input_nodes

    async def execute(self, ctx) -> list:
        return ctx.inputs.outputs[0]

@dataclass
class Neuron(Node):
    w: np.ndarray
    b: float
    lr: float
    activation: 'ActivationFunction'
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

    def toggle_train_mode(self):
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
        ctx.workflow
        mode = ctx.inputs.outputs[0][0]
        if mode == 'apply_grads':
            self.apply_grads()
            return ('apply_grads', None)
        elif mode == 'zero_grads':
            self.zero_grads()
            return ('zero_grads', None)
        elif mode == 'forward':
            return ('forward', self.forward([r[1] for r in ctx.inputs.outputs]))
        elif mode == 'backward':
            return ('backward', self.backward([r[1] for r in ctx.inputs.outputs]))
        else:
            raise ValueError(f'Invalid mode `{mode}`')
    

@dataclass
class LossFunction(ABC):
    @abstractmethod
    def forward(self, y, y_pred) -> Any: ...
    @abstractmethod
    def backward(self, y, y_pred) -> Any: ...

@dataclass
class L2(LossFunction):
    def forward(self, y, y_pred):
        return (y_pred - y) ** 2
    
    def backward(self, y, y_pred):
        return 2 * (y_pred - y)

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
class Sigmoid(ActivationFunction):
    def forward(self, z):
        return 1 / (1 + np.exp(-z))
    
    def backward(self, z):
        return self.forward(z) * (1 - self.forward(z))


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

def circle_data_generator(samples, r):
    square_side = 1/2 * r * (2 * np.pi) ** (1/2)
    x1_x2 = square_side * 2 * (np.random.random((samples, 2)) - 1/2)
    y_real = np.array([1 if (x**2 + y**2) < r**2 else 0 for x, y in x1_x2]).tolist()
    return [((x1, x2), y) for (x1, x2), y in zip(x1_x2, y_real)]

def plot_train_graph(xy_data, y_pred, scatter_xy_data, loss, pause):
    xy = np.asarray([xyd[0] for xyd in xy_data])
    y_pred = np.asarray(y_pred)
    xs = np.linspace(-AX_LIM, AX_LIM, GRID_RES)
    ys = np.linspace(-AX_LIM, AX_LIM, GRID_RES)
    xx, yy = np.meshgrid(xs, ys)
    zi = griddata(
        xy,
        y_pred,
        (xx, yy),
        method="linear",
        fill_value=0.0
    )
    heatmap.set_data(zi)

    scatter_class_1.set_offsets([xyd[0] for xyd in scatter_xy_data if xyd[1] >= 0.5])
    scatter_class_0.set_offsets([xyd[0] for xyd in scatter_xy_data if xyd[1] < 0.5])

    line_loss.set_data(list(range(len(loss))), loss)
    ax_loss.relim()
    ax_loss.autoscale_view()
    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    plt.tight_layout()
    plt.pause(pause)

def toggle_train_mode(nn: list[list[Neuron] | list[NeuronInput]]):
    for node in nn[0][0].workflow.sessions['s1'].nodes.values():
        node.toggle_train_mode()

async def run(exec_id: str, node: Node, mode: str, inputs = None):
    return await node.run(NodeIO(
        source=NodeIOSource(session_id=f's1', execution_id=exec_id, node=None),
        status=NodeIOStatus(),
        output=(mode, inputs),
    ))

async def train_nn(nn: list[list[Neuron] | list[NeuronInput]], xy_data):
    mini_batch_size = int(len(xy_data) * 0.2)
    train_loss = []
    loss_function = L2()

    for epoch in range(100):
        random.shuffle(xy_data)
        
        batch_loss = []
        y_pred = []
        
        for mini_batch_xy_data in batched(xy_data, mini_batch_size):

            mini_batch_y_pred = []
            for xn, y in mini_batch_xy_data:

                forward = sum(await asyncio.gather(*[
                    run(str(epoch), input_neuron, 'forward', [x])
                    for input_neuron, x in zip(nn[0], xn)
                ]), [])[0].output[1][0]
                batch_loss.append(loss_function.forward(y, forward))

                y_pred.append(forward)
                mini_batch_y_pred.append(forward)

                # dL = (forward - y)

                toggle_train_mode(nn)
                await run(str(epoch), nn[-1][0], 'backward', [loss_function.backward(y, forward)])
                toggle_train_mode(nn)

            # plot_train_graph(mini_batch_xy_data, mini_batch_y_pred, xy_data, train_loss, 0.001)
                
            toggle_train_mode(nn)
            await run(str(epoch), nn[-1][0], 'apply_grads')
            await run(str(epoch), nn[-1][0], 'zero_grads')
            toggle_train_mode(nn)

        train_loss.append(np.mean(batch_loss))
        print(f'Epoch: {epoch}, loss: {train_loss[-1]:.2f}, x: ({xn[0]:.2f}, {xn[1]:.2f}), y: {y}, y_pred: {y_pred[-1]:.2f}')

        plot_train_graph(xy_data, y_pred, xy_data, train_loss, 0.001)
    
    plot_train_graph(xy_data, y_pred, xy_data, train_loss, 0)


CIRCUMFERENCE_RADIUS = 1
AX_LIM = CIRCUMFERENCE_RADIUS * 1/2 * (2 * np.pi) ** (1/2)
GRID_RES = 100

plt.ion()
fig, (ax_heatmap, ax_loss) = plt.subplots(1, 2, figsize=(12, 6))
ax_heatmap.set_xlim(-AX_LIM, AX_LIM)
ax_heatmap.set_ylim(-AX_LIM, AX_LIM)
ax_heatmap.set_title("Heatmap (x1, x2) → y")
scatter_class_1 = ax_heatmap.scatter([], [], alpha=1, label="1", color='blue', marker='o', edgecolors='white', s=30)
scatter_class_0 = ax_heatmap.scatter([], [], alpha=1, label="0", color='red', marker='o', edgecolors='white', s=30)
heatmap = ax_heatmap.imshow(
    np.zeros((GRID_RES, GRID_RES)),
    extent=(-AX_LIM, AX_LIM, -AX_LIM, AX_LIM),
    origin="lower",
    cmap=LinearSegmentedColormap.from_list(
        "RB",
        ["lightcoral", "dodgerblue"]
    ),
    vmin=0.0, vmax=1.0, aspect="auto"
)
line_loss, = ax_loss.plot([], [], lw=2)
ax_loss.set_title("Loss")
ax_loss.set_xlabel("Epoch")
ax_loss.set_ylabel("Loss")
ax_loss.grid(True)
plt.colorbar(heatmap, ax=ax_heatmap, label="y")


nn = mlp_generator(
    architecture=[
        (2, ReLU()), 
        (5, ReLU()), 
        (5, ReLU()),
        (1, ReLU())
    ],
    lr=0.001
)
# nn[0][0].plot(show_methods=False)

xy_data = circle_data_generator(samples=1000, r=CIRCUMFERENCE_RADIUS)

asyncio.run(train_nn(nn, xy_data))


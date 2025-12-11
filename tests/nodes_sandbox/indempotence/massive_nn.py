import random
import time
from typing import ClassVar
from src.models.node import NodeIO, NodeIOFlags, NodeProcessorConfig
from src.nodes.node import Node, NodeProcessor, NodeIOSource
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print
from config import settings
from itertools import combinations

@dataclass
class NeuronInput(NodeProcessor):
    async def execute(self) -> float:
        return self.inputs[settings.node.first_execution_source].result

@dataclass
class Neuron(NodeProcessor):
    w: np.ndarray
    b: float
    config = NodeProcessorConfig(deep_copy_fields=True)

    async def execute(self) -> float:
        x = np.array(self.inputs.results)
        z = x @ self.w + self.b
        a = max(z, 0.)
        return float(a)
    
def neuron(x: float, y: float) -> np.ndarray:
    a1 = np.array([[x, y]]) @ np.array([[-0.69, -0.77], [-0.26, +0.97], [+0.95, -0.19]]).T + np.array([-0.23, -0.29, -0.27])
    a1[a1 < 0] = 0.
    a2 = a1 @ np.array([0.93, 0.99, 0.93]) + np.array([-1.4])
    a2[a2 < 0] = 0.
    a3 = a2 @ np.array([-1]) + np.array([1])
    a3[a3 < 0] = 0.
    return a3

def mlp_generator(label: str, architecture: list[int]) -> list[list[Node]]:
    inputs = [
        Node(name=f"{label}_input_{i}", processor=NeuronInput())
        for i in range(architecture[0])
    ]
    layers: list[list[Node]] = []
    for layer_index, layer_size in enumerate(architecture[1:]):
        layer = []
        for neuron_index in range(layer_size):
            layer.append(
                Node(
                    name=f"{label}_L{layer_index}_N{neuron_index})", 
                    processor=Neuron(
                        w=np.random.rand(architecture[layer_index]), 
                        b=random.randint(0, 1)
                    )
                )
            )
        layers.append(layer)
    layers.insert(0, inputs)
    for current_layer, next_layer in zip(layers, layers[1:]):
        for current_neuron in current_layer:
            for next_neuron in next_layer:
                current_neuron.connect(next_neuron)
    return layers

def batch_runs(label: str, runs: int, nn_architecture: list[int]):
    random.seed(0)
    np.random.seed(0)
    multiple_runs = []
    for run in range(runs):
        mlp = mlp_generator(f'{label}_{run}', nn_architecture)
        for input in mlp[0]:
            multiple_runs.append(input.run(NodeIO(
                source=NodeIOSource(id=f'user_nn', execution_id=f'nn', node=None),
                result=random.uniform(-1, 1),
                flags=NodeIOFlags(),
            )))
    
    random.seed(int(label))
    np.random.seed(int(label))
    random.shuffle(multiple_runs)

    return multiple_runs

async def main():
    t0 = time.perf_counter()
    
    batches = 50
    runs_per_batch = 100
    # nn_architecture = [4, 10, 10, 10, 10, 10, 10, 10, 4, 10, 1, 10, 1, 10, 1]
    nn_architecture = [4, 10, 10, 10, 10, 10, 1]
    
    batches_results = []
    for i in range(batches):
        batches_results.append([
            r.result for r in sum(await asyncio.gather(*batch_runs(f'{i}', runs_per_batch, nn_architecture)), [])
        ])

    t1 = time.perf_counter()

    for pair in combinations(batches_results, 2):
        assert len(pair) == 2
        assert pair[0] != pair[1]
        assert sorted(pair[0]) == sorted(pair[1])

    print(f'🟢 NN Consistency Test Passed')
    print(f'Total runs: {batches * runs_per_batch}')
    print('Total nodes: ', sum(nn_architecture) * batches * runs_per_batch)
    print(f'Total Time: {t1 - t0:.2f}')
    print(f'Time per run: {(t1 - t0) / (batches * runs_per_batch)}')
    print(f'Time per node: {(t1 - t0) / (batches * runs_per_batch * sum(nn_architecture))}')

    

asyncio.run(main())
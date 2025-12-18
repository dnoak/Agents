import random
import time
from typing import ClassVar
from nodesio.models.node import NodeIO, NodeIOStatus, NodeExecutorConfig, NodeExternalInput, NodeIOSource
from nodesio.engine.node import Node
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print
from itertools import combinations

@dataclass
class NeuronInput(Node):
    async def execute(self) -> float:
        return self.inputs[NodeExternalInput].result

@dataclass
class Neuron(Node):
    w: np.ndarray
    b: float
    config = NodeExecutorConfig(deep_copy_fields=True)

    async def execute(self) -> float:
        x = np.array(self.inputs.results)
        z = x @ self.w + self.b
        a = max(z, 0.)
        return float(a)
    
def np_execute_benchmark(size: int) -> float:
    w = np.array(np.random.rand(size), dtype=np.float32)
    x = np.array(np.random.rand(size), dtype=np.float32)
    z = x.T @ w + 0.123
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

def mlp_generator(label: str, architecture: list[int]) -> list[list[Neuron] | list[NeuronInput]]:
    global NEURON
    inputs = [
        NeuronInput(name=f"{label}_input_{i}")
        for i in range(architecture[0])
    ]
    layers: list[list[Neuron] | list[NeuronInput]] = []
    for layer_index, layer_size in enumerate(architecture[1:]):
        layer = []
        for neuron_index in range(layer_size):
            layer.append(
                Neuron(
                    name=f"{label}_L{layer_index}_N{neuron_index}", 
                    w=np.random.rand(architecture[layer_index]), 
                    b=random.randint(0, 1)
                )
            )
        layers.append(layer)
    layers.insert(0, inputs)
    for current_layer, next_layer in zip(layers, layers[1:]):
        for current_neuron in current_layer:
            for next_neuron in next_layer:
                current_neuron.connect(next_neuron)
    NEURON = layers[-1][-1]
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
                status=NodeIOStatus(),
            )))
    
    random.seed(int(label))
    np.random.seed(int(label))
    random.shuffle(multiple_runs)

    # print(mlp[0][0].metrics)
    # mlp[0][0].plot(sleep=1)

    return multiple_runs

async def main():
    global NEURON
    
    batches = 1
    runs_per_batch = 1
    nn_architecture = [4, 10, 10, 10, 10, 10, 10, 10, 4, 10, 1, 10, 1, 10, 1]
    # nn_architecture = [4, 5, 5, 5, 5, 1]
    # nn_architecture = [2,500,500,500,500,500] # 1 mi
    
    batches_results = []
    batches_times = []
    for b in range(batches):
        batches_runs = batch_runs(f'{b}', runs_per_batch, nn_architecture)
        
        t0 = time.perf_counter()
        batches_results.append([
            r.result for r in sum(await asyncio.gather(*batches_runs), [])
        ])
        t1 = time.perf_counter()
        batches_times.append(t1 - t0)

        print(f'Batch {b} took {t1 - t0} seconds')

    for pair in combinations(batches_results, 2):
        assert len(pair) == 2
        assert pair[0] != pair[1]
        assert sorted(pair[0]) == sorted(pair[1])


    total_runs = batches * runs_per_batch
    total_node_runs = sum(nn_architecture) * total_runs
    total_connections = total_node_runs * sum(a*b for a, b in zip(nn_architecture, nn_architecture[1:]))
    total_time = sum(batches_times)
    
    print(f'🟢 NN Consistency Test Passed')
    print(f'Total runs: {total_runs}')
    print(f'Total node runs: {total_node_runs}')
    print(f'Total connections: {total_connections}')
    print(f'Total Time: {total_time}')
    print(f'Time per run: {(total_time) / total_runs}')
    print(f'Time per node: {(total_time) / total_node_runs}')


asyncio.run(main())
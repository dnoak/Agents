import random
from typing import ClassVar
from src.models.node import NodeIO, NodeIOFlags, NodeProcessorConfig
from src.nodes.node import Node, NodeProcessor, NodeIOSource
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print
from config import settings

@dataclass
class NeuronInput(NodeProcessor):
    config = NodeProcessorConfig(blablabla='🔴🟢')
    async def execute(self) -> float:
        return self.inputs[settings.node.first_execution_source].result

@dataclass
class Neuron(NodeProcessor):
    w: list[float]
    b: float
    config = NodeProcessorConfig(deep_copy_fields=True)

    async def execute(self) -> float:
        b = self.b
        w0 = self.w[0]
        self.b = -100
        self.w[0] = -100
        await asyncio.sleep(random.uniform(0, 0.1))
        self.b = b
        self.w[0] = w0

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
    

async def nn():
    nx = Node(name="nx", processor=NeuronInput())
    ny = Node(name="ny", processor=NeuronInput())
    
    n11 = Node(name="n11", processor=Neuron(w=[-0.69, -0.77], b=-0.23))
    n12 = Node(name="n12", processor=Neuron(w=[-0.26, +0.97], b=-0.29))
    n13 = Node(name="n13", processor=Neuron(w=[+0.95, -0.19], b=-0.27))

    n21 = Node(name="n21", processor=Neuron(w=[0.93, 0.99, 0.93], b=-1.4))
    n31 = Node(name="n31", processor=Neuron(w=[-1], b=1))

    nx.connect(n11)
    nx.connect(n12)
    nx.connect(n13)
    ny.connect(n11)
    ny.connect(n12)
    ny.connect(n13)

    n11.connect(n21)
    n12.connect(n21)
    n13.connect(n21)
    
    n21.connect(n31)
    # nx.plot()
    

    xy = [(round(random.uniform(-4, 4),2), round(random.uniform(-4, 4),2)) for _ in range(200)]
    outputs = []
    # real_outputs = []
    for i, (x, y) in enumerate(xy):
        inputs = [
            nx.run(NodeIO(
                source=NodeIOSource(id=f'user_nn{i}', execution_id=f'{i}', node=None),
                result=x,
                flags=NodeIOFlags(),
            )),
            ny.run(NodeIO(
                source=NodeIOSource(id=f'user_nn{i}', execution_id=f'{i}', node=None),
                result=y,
                flags=NodeIOFlags(),
            )),
        ]
        outputs += inputs

    random.shuffle(outputs)

    results: list[NodeIO] = sum(await asyncio.gather(*outputs), [])
    results.sort(key=lambda x: int(x.source.execution_id))

    for exec_id, exec in nx.executions.executions.items():
        assert {exec_id} == set(v.source.execution_id for v in exec.values()) 

    for i, ((x, y), res) in enumerate(zip(xy, results)):

        batch_nodes_output = res.result
        real_output = neuron(x, y)[0]
        unique_nodes = [
            nx.run(NodeIO(
                source=NodeIOSource(id=f'user_nn{i}', execution_id=f'a{i}', node=None),
                result=x,
                flags=NodeIOFlags(),
            )),
            ny.run(NodeIO(
                source=NodeIOSource(id=f'user_nn{i}', execution_id=f'a{i}', node=None),
                result=y,
                flags=NodeIOFlags(),
            )),
        ]
        unique_nodes_output = sum(await asyncio.gather(*unique_nodes), [])[0].result

        assert1 = (batch_nodes_output != real_output) * '🔴 '
        assert2 = (unique_nodes_output != real_output) * '🔴 '
        
        print(f'exec_id: {res.source.execution_id}')
        print(f'x: {x}, y: {y}')
        print(f'real  : {real_output}')
        print(f'{assert1}batch : {batch_nodes_output}')
        print(f'{assert2}unique: {unique_nodes_output}')
        if assert1:
            batch_exec = nx.executions.executions[res.source.execution_id]
            unique_exec = nx.executions.executions[f'a{i}']
            assert set(batch_exec.keys()) == set(unique_exec.keys())
            for node_name in batch_exec.keys():
                node_batch_exec = nx.executions.executions[res.source.execution_id][node_name]
                node_unique_exec = nx.executions.executions[f'a{i}'][node_name]

                try:
                    wb = node_batch_exec.source.node.processor.w
                    bb = node_batch_exec.source.node.processor.b
                    wu = node_unique_exec.source.node.processor.w
                    bu = node_unique_exec.source.node.processor.b
                except:
                    wb = '__input__'
                    bb = ''
                    wu = '__input__'
                    bu = ''
                print()
                print(f'node: {node_name}')
                print(f'batch : {node_batch_exec.result}, {wb}, {bb}')
                print(f'unique: {node_unique_exec.result}, {wu}, {bu}')
            input()
        print()
        # assert res.result == rout[0]
        assert real_output == batch_nodes_output
        assert real_output == unique_nodes_output

    # print(nx.executions.get('id0'))

    # print(nx.inputs_queue.pending, nx.inputs_queue.futures)
    # print(ny.inputs_queue.pending, ny.inputs_queue.futures)
    # print(n11.inputs_queue.pending, n11.inputs_queue.futures)
    # print(n12.inputs_queue.pending, n12.inputs_queue.futures)
    # print(n13.inputs_queue.pending, n13.inputs_queue.futures)
    # print(n21.inputs_queue.pending, n21.inputs_queue.futures)
    # print(n31.inputs_queue.pending, n31.inputs_queue.futures)
    

asyncio.run(nn())
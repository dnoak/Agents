import random
from nodesio.engine.node import Node
from nodesio.models.node import (
    NodeIO, 
    NodeIOStatus, 
    NodeExecutorConfig, 
    NodeExternalInput,
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
class Neuron(Node):
    w: list[float]
    b: float

    async def execute(self) -> float:
        # 🔴 changing values in concurrent executions #
        if self.inputs._inputs[0].source.session_id.startswith('modified'):
            self.w = [random.random() for w in self.w]
            self.b = random.random()

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
    return a3.astype(np.float32)

def nn():
    nx = NeuronInput(name="nx")
    ny = NeuronInput(name="ny")
    
    n11 = Neuron(name="n11", w=[-0.69, -0.77], b=-0.23)
    n12 = Neuron(name="n12", w=[-0.26, +0.97], b=-0.29)
    n13 = Neuron(name="n13", w=[+0.95, -0.19], b=-0.27)

    n21 = Neuron(name="n21", w=[0.93, 0.99, 0.93], b=-1.4)
    n31 = Neuron(name="n31", w=[-1], b=1)

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
    
    return nx, ny
    
async def main():

    nx, ny = nn()

    xy = [(round(random.uniform(-4, 4),2), round(random.uniform(-4, 4),2)) for _ in range(10)]
    
    outputs = {'inputs': [], 'modified_inputs': [], 'real_output': []}
    for i, (x, y) in enumerate(xy):
        inputs = [
            nx.run(NodeIO(
                source=NodeIOSource(session_id=f'user_nn{i}', execution_id=f'{i}', node=None),
                result=x,
                status=NodeIOStatus(),
            )),
            ny.run(NodeIO(
                source=NodeIOSource(session_id=f'user_nn{i}', execution_id=f'{i}', node=None),
                result=y,
                status=NodeIOStatus(),
            )),
        ]
        modified_inputs = [
            nx.run(NodeIO(
                source=NodeIOSource(session_id=f'modified_user_nn{i}', execution_id=f'modified_{i}', node=None),
                result=x,
                status=NodeIOStatus(),
            )),
            ny.run(NodeIO(
                source=NodeIOSource(session_id=f'modified_user_nn{i}', execution_id=f'modified_{i}', node=None),
                result=y,
                status=NodeIOStatus(),
            )),
        ]
        outputs['inputs'] += inputs
        outputs['modified_inputs'] += modified_inputs
        outputs['real_output'].append(neuron(x, y)[0])

    # 🔴 breaking the order of inputs arrival
    grouped = outputs['inputs'] + outputs['modified_inputs']
    random.shuffle(grouped)

    processed_outputs = sum(await asyncio.gather(*grouped), [])
    node_outputs = list(filter(lambda x: x.source.session_id.startswith('user_nn'), processed_outputs))
    node_outputs.sort(key=lambda x: int(x.source.execution_id))
    
    modified_node_outputs = list(filter(lambda x: x.source.session_id.startswith('modified_user_nn'), processed_outputs))
    modified_node_outputs.sort(key=lambda x: int(x.source.execution_id.replace('modified_', '')))

    for (x, y), real_output, node_output, modified_node_output in zip(xy, outputs['real_output'], node_outputs, modified_node_outputs):
        assert {node_output.source.execution_id} == set(
            e.source.execution_id for e in
            nx._executions[node_output.source.execution_id].values()
        )
        assert real_output == node_output.result, f'real: {real_output}, nodes: {node_output.result}'
        
        assert real_output != modified_node_output.result, f'real: {real_output}, mod_nodes: {modified_node_output.result}'
        
        print(f'exec_id: {node_output.source.execution_id}')
        print(f'x: {x}, y: {y}')
        print(f'real : {real_output}')
        print(f'nodes: {node_output.result}')
        print(f'modified_nodes: {modified_node_output.result}')
        print()



asyncio.run(main())
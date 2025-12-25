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
        b = self.b
        w0 = self.w[0]
        self.b = -100
        self.w[0] = -100
        # 🟡 randomizing processor order
        await asyncio.sleep(random.uniform(0, 1))
        self.b = b
        self.w[0] = w0
        # # # # # # # # # # # # # # # # # # # # # # #

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

    xy = [(round(random.uniform(-4, 4),2), round(random.uniform(-4, 4),2)) for _ in range(100)]
    outputs = []
    real_outputs = []
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
        outputs += inputs
        real_outputs.append(neuron(x, y)[0])

    # 🔴 breaking the order of inputs arrival

    random.shuffle(outputs)
    nx.plot()

    node_outputs: list[NodeIO] = sum(await asyncio.gather(*outputs), [])
    node_outputs.sort(key=lambda x: int(x.source.execution_id))

    for (x, y), real_output, node_output in zip(xy, real_outputs, node_outputs):
        # assert {node_output.source.execution_id} == set(
        #     e.source.execution_id for e in
        #     nx._graph_executions[node_output.source.execution_id].values()
        # )
        assert real_output == node_output.result, f'real: {real_output}, nodes: {node_output.result}'
        
        print(f'exec_id: {node_output.source.execution_id}')
        print(f'x: {x}, y: {y}')
        print(f'real : {real_output}')
        print(f'nodes: {node_output.result}')
        print()



asyncio.run(main())
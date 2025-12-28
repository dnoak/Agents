import random
from typing import Any
import uuid
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print

@dataclass
class Neuron(Node):
    lr: float = 0.001 # Reduzi um pouco a LR
    w: np.ndarray = field(init=False)
    b: float = field(init=False)
    w_grad: np.ndarray = field(init=False)
    b_grad: float = field(init=False)
    x: np.ndarray = field(init=False)
    z: np.ndarray = field(init=False)
    a: np.ndarray = field(init=False)

    def init_wandb(self):
        # Inicialização He/Xavier simplificada (menor variância)
        self.w = np.random.randn(max(len(self._input_nodes), 1)) * 0.1
        self.b = 0.0
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
        
        # Derivada da Ativação (ReLU)
        dadz = 1 if self.z > 0 else 0 
        
        # Gradiente Local (Chain Rule part 1)
        local_grad = delta * dadz

        # CORREÇÃO MATEMÁTICA AQUI:
        # Para atualizar W, usamos X.
        self.w_grad += local_grad * self.x
        self.b_grad += local_grad
        
        # Para retornar para trás, usamos W.
        return local_grad * self.w

    def forward(self, inputs: list[float]) -> np.ndarray:
        self.x = np.array(inputs).T
        # Garante dimensão correta para produto escalar
        if self.x.shape != self.w.shape:
             # Fallback simples caso venha lista crua
             self.x = np.resize(self.x, self.w.shape)

        self.z = self.x @ self.w + self.b
        self.a = np.maximum(self.z, 0) # ReLU
        return self.a

    async def execute(self, ctx) -> tuple[str, Any]:
        mode = ctx.inputs.results[0][0]
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

        values = [r[1] for r in ctx.inputs.results]
        if mode == 'forward':
            return ('forward', self.forward(values))
        elif mode == 'backward':
            return ('backward', self.backward(values))
        else:
            raise ValueError(f'Invalid mode `{mode}`')

# --- CONFIGURAÇÃO DA REDE ---
a = Neuron(name='a')
b = Neuron(name='b')

# Topologia simples: Input -> A -> B -> Output
# Nota: Como 'a' é o primeiro nó, o input do usuário entra nele.
# 'b' é o último nó.
a.connect(b)

def init_wandb():
    for node in [a, b]:
        node.init_wandb()

async def toggle_backward_mode():
    # Toggle em todos os nós envolvidos
    for node in [a, b]:
        node.toggle_backward_mode()

async def apply_grads():
    # Dispara o apply grads em cascata (assumindo que o framework propague)
    # Ou chama manualmente para o teste:
    await a.run(NodeIO(
        source=NodeIOSource(session_id='s1', execution_id=str(uuid.uuid4())[:5], node=None),
        result=('apply_grads', None),
        status=NodeIOStatus(),
    ))

async def forward(inputs: list[float]):
    # Executa o nó A, que deve passar para o B.
    # O resultado final que queremos é o de B.
    # Dependendo da sua lib, 'a.run' pode não retornar o resultado de 'b'.
    # Aqui assumo que precisamos rodar a cadeia e pegar o output de B.
    
    # Simulação manual da execução sequencial para garantir o teste:
    res_a = await a.run(NodeIO(source=NodeIOSource(session_id='s1', execution_id='ex', node=None), result=('forward', inputs), status=NodeIOStatus()))
    
    # Se sua lib não encadeia automaticamente o retorno final no 'res_a',
    # você precisa pegar o output de A e passar para B manualmente neste teste:
    input_b = res_a[0].result[1] # Output de A
    res_b = await b.run(NodeIO(source=NodeIOSource(session_id='s1', execution_id='ex', node=None), result=('forward', [input_b]), status=NodeIOStatus()))
    
    return res_b

async def backward(loss_grad: list[float]):
    # CORREÇÃO DE TOPOLOGIA: Começa pelo B (último nó), não G
    return await b.run(NodeIO(
        source=NodeIOSource(session_id='s1', execution_id=str(uuid.uuid4())[:5], node=None),
        result=('backward', loss_grad),
        status=NodeIOStatus(),
    ))

async def train_step(x: float, y: float):
    # Forward Pass
    final_output_node = await forward([x])
    prediction = final_output_node[0].result[1] # Supondo array numpy
    if isinstance(prediction, np.ndarray): prediction = prediction[0]

    # Cálculo do Gradiente da Loss (MSE)
    # dL/dy_pred = 2 * (y_pred - y)
    dL = 2 * (prediction - y)

    # Backward Pass
    await toggle_backward_mode()
    await backward([dL])
    await toggle_backward_mode() # Volta ao normal
    
    # Update Weights
    await apply_grads()

    if random.random() < 0.05: # Print esporádico
        print(f'Pred: {prediction:.4f}, Real: {y:.4f}, Loss: {(prediction-y)**2:.4f}')

# --- DADOS NORMALIZADOS ---
# Redes Neurais odeiam números grandes não normalizados
data = [(i/100.0, 2*(i/100.0)) for i in np.arange(100)] 

init_wandb()

print("--- Começando Treino ---")
for epoch in range(50): # Mais épocas
    random.shuffle(data)
    for x, y in data:
        asyncio.run(train_step(x, y))
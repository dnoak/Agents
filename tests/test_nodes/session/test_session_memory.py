import asyncio
from dataclasses import dataclass, field
import random
import time
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeExecutorConfig, NotProcessed
from rich import print

@dataclass
class Message:
    message: int
    send_to: str
    save_in_node_memory: bool
    save_in_session_memory: bool

@dataclass
class MessageReceiver(Node):
    config = NodeExecutorConfig(routing_default_policy='clear')

    async def execute(self, ctx) -> Message:
        message: Message = ctx.inputs.outputs[0]
        ctx.routing.add(message.send_to)
        return message

@dataclass
class BranchA(Node):
    node_a_memory: list[str]
    
    async def execute(self, ctx) -> dict:
        message: Message = ctx.inputs.outputs[0]
        
        if message.save_in_node_memory:
            self.node_a_memory.append(f'a{message.message}')

        if message.save_in_session_memory:
            ctx.session.memory.facts.append(f'a{message.message}')
        
        return {
            'message': message.message,
            'node_a_memory': self.node_a_memory,
            'session_memory': ctx.session.memory.facts,
        }

@dataclass
class BranchB(Node):
    node_b_memory: list[str]
    
    async def execute(self, ctx) -> dict:
        message: Message = ctx.inputs.outputs[0]
        
        if message.save_in_node_memory:
            self.node_b_memory.append(f'b{message.message}')

        if message.save_in_session_memory:
            ctx.session.memory.facts.append(f'b{message.message}')
        
        return {
            'message': message.message,
            'node_b_memory': self.node_b_memory,
            'session_memory': ctx.session.memory.facts,
        }

@dataclass
class Result(Node):
    async def execute(self, ctx) -> int:
        return ctx.inputs.outputs[0]

messager_receiver = MessageReceiver(name='messager_receiver')
branch_a = BranchA(name='branch_a', node_a_memory=[])
branch_b = BranchB(name='branch_b', node_b_memory=[])
result_node = Result(name='result_node')

messager_receiver.connect(branch_a)
messager_receiver.connect(branch_b)
branch_a.connect(result_node)
branch_b.connect(result_node)



# 🟥🟥🟥 teste 🟥🟥🟥 
# envia números de 1 a 100
# para o nó a:
# - só entra no nó quando o número é par
# - salva na memória do nó se o número for divisível por 7
# para o nó b:
# - só entra no nó quando o número é ímpar
# - salva na memória do nó se o número for divisível por 7
# salva os números divisíveis por 9 na memória da sessão (em ambos nós)

async def main():
    messages = [
        Message(
            message=i,
            send_to='branch_a' if i % 2 == 0 else 'branch_b',
            save_in_node_memory=(i % 7 == 0),
            save_in_session_memory=(i % 9 == 0),
        )
        for i in range(1, 101)
    ]

    total_runs: list[list[NodeIO]] = []
    for eid, message in enumerate(messages):

        batch_runs = []
        for sid in range(10):
            result = messager_receiver.run(NodeIO(
                source=NodeIOSource(session_id=f's{sid+1}', execution_id=f'e{eid+1}', node=None),
                status=NodeIOStatus(),
                output=message,
            ))
            batch_runs.append(result)

        random.shuffle(batch_runs)

        total_runs.append(sum(await asyncio.gather(*batch_runs), []))
    
    for evens in total_runs[-1]: # execution 100
        results = [int(x[1:]) for x in evens.output['node_a_memory']]
        node_a = [x[0] for x in evens.output['node_a_memory']]

        assert evens.output['message'] == 100, f'message: {evens.output["message"]}'
        assert set(node_a) == {'a'}, f'node_a: {node_a}'
        assert all((x % 7 == 0) and (x % 2 == 0) for x in results), f'results: {results}'

    for odds in total_runs[-2]:  # execution 99
        results = [int(x[1:]) for x in odds.output['node_b_memory']]
        node_b = [x[0] for x in odds.output['node_b_memory']]

        assert odds.output['message'] == 99, f"message: {odds.output['message']}"
        assert set(node_b) == {'b'}, f"node_b: {node_b}"
        assert all((x % 7 == 0) and (x % 2 == 1) for x in results), f"results: {results}"

    for last in total_runs[-1]:  # execution 100        
        for result in last.output['session_memory']:
            node = result[0]
            value = int(result[1:])
            if node == 'a':
                assert value % 9 == 0 and value % 2 == 0, f"node: {node}, value: {value}"
            elif node == 'b':
                assert value % 9 == 0 and value % 2 == 1, f"node: {node}, value: {value}"
            else:
                assert False, f"node: {node}, value: {value}"
            




asyncio.run(main())
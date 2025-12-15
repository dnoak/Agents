import asyncio
from dataclasses import dataclass, field
from nodesio.engine.node import Node
from nodesio.models.node import NodeIO, NodeIOStatus, NodeIOSource, NodeOperatorConfig
from rich import print

@dataclass
class Alphabet(Node):
    rere: str

    async def execute(self) -> str:
        print(self.name)
        return 'Hello world!'
    

a = Alphabet('rere', name='a', config=NodeOperatorConfig(deep_copy_fields=True))
b = Alphabet(name='b', rere='rere')
c = Alphabet(name='c', rere='rere')

a.connect(b)
a.connect(c)

print(a.config)
print(b.config)
print(c.config)

async def main():
    res = await a.run(NodeIO(
        source=NodeIOSource(id='user', execution_id='user', node=None),
        result='Hello world!',
        status=NodeIOStatus(),
    ))
    print(res)

asyncio.run(main())

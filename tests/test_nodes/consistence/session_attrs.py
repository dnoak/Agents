from collections import defaultdict
import random
from typing import Any
import uuid
from nodesio.engine.node import Node
from nodesio.models.node import (
    NodeExternalInput,
    NodeExecutorConfig,
    NodeIO, 
    NodeExecutorContext,
    NotProcessed,
    NodeIOStatus, 
    NodeIOSource,
)
from dataclasses import dataclass, field
import asyncio
import numpy as np
from rich import print

@dataclass
class Alphabet(Node): 
    l: list[str]

    async def execute(self, ctx: NodeExecutorContext) -> list[str]:
        # ctx.routing.skip('b')
        # self.routing
        self.l += [ctx.execution_id]
        return self.l

alfa = Alphabet(name='a', l=[])
beta = Alphabet(name='b', l=[])
# c = Alphabet(name='c', l=['c'])

alfa.connect(beta)

batches = 100
sessions = list(map(lambda x: f's{x}', range(100)))

runs_args: list[list[tuple[str, int]]] = []
for batch in range(batches):
    run = []
    for session in sessions:
        if random.choice([True, False]):
            run.append((session, random.randint(0, 100)))
    runs_args.append(run)

results = {}
async def main():
    for batch in runs_args:
        batch_run = [
            alfa.run(input=NodeIO(
                source=NodeIOSource(
                    session_id=session, 
                    execution_id=str(eid), 
                    node=None
                ),
                result=['_in_'],
                status=NodeIOStatus()
            ))
            for session, eid in batch
        ]
        for result in sum(await asyncio.gather(*batch_run), []):
            # if not isinstance(result.result, NotProcessed):
            results[result.source.session_id] = result.result

asyncio.run(main())

# print(results)

gathered_runs_args = defaultdict(list)
for run_args in runs_args:
    for session, eid in run_args:
        gathered_runs_args[session].append(str(eid))

# print(dict(gathered_runs_args))

for a, b in zip(gathered_runs_args.values(), results.values()):
    assert sum(map(int, a)) == sum(map(int, b))
    # print(a)

async def check_results():
    for session in results.keys():
        res = await alfa.run(input=NodeIO(
            source=NodeIOSource(
                session_id=session, 
                execution_id='test', 
                node=None
            ),
            result=['_in_'],
            status=NodeIOStatus()
        ))
        print(f'session {session}: {res[0].result}')

asyncio.run(check_results())

import asyncio
from nodesIO.engine.node import Node
from nodesIO.models.node import NodeIO, NodeIOStatus, NodeIOSource
from dataclasses import dataclass
from rich import print

@dataclass
class Start(Node):
    async def execute(self, ctx) -> list[str]:
        self._input_nodes = ctx.inputs.outputs[0]['input_nodes']
        self._output_nodes = ctx.inputs.outputs[0]['output_nodes']
        return []

@dataclass
class Route(Node):
    async def execute(self, ctx) -> list[str]:
        return sum([i.output for i in ctx.inputs], []) + [self.name] # flatten

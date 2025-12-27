import time
import datetime
import asyncio
from dataclasses import dataclass, make_dataclass
import dataclasses
from rich import print
from nodesio.engine.node import Node

n = type('Node', (Node,), {})

nodex = n(name='nodex', _constructor_node=False)
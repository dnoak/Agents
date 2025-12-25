from nodesio.engine.node import Node
from dataclasses import field
from pympler import asizeof
from rich import print
import matplotlib.pyplot as plt

class TestClass:
    var1: int = 0
    var2: list[list[int]] = field(default_factory=lambda: [[0]])
    var3: list[list[int]] = field(default_factory=lambda: [[0]])

class MemoryNode(Node):
    var1: int = 0
    var2: list[list[int]] = field(default_factory=lambda: [[0]])
    var3: TestClass = field(default_factory=TestClass)

    def tool1(self):
        pass
    def tool2(self):
        pass
    def tool3(self):
        pass
    async def execute(self):
        self.tool1()
        self.tool2()
        self.tool3()


nodes: list[MemoryNode] = []
individual_memory_usages = []
accumulated_memory_usage = []

for i in range(1000):
    nodes.append(MemoryNode(name=f'node{i}'))
    individual_memory_usages.append(asizeof.asizeof(nodes[-1]) / (1024 ** 2))
    accumulated_memory_usage.append(asizeof.asizeof(nodes) / (1024 ** 2))

# plot 2 graphs in the same figure
fig, ax = plt.subplots(2, 1, sharex=True)
ax[0].plot(range(len(individual_memory_usages)), individual_memory_usages)
ax[0].set_title('Memory usage (mb)')
ax[0].set_ylabel('Memory usage (mb)')
ax[0].set_xlabel('[i] Node')
ax[0].grid()

ax[1].plot(range(len(individual_memory_usages)), accumulated_memory_usage)
ax[1].set_title('Accumulated memory usage (mb)')
ax[1].set_ylabel('Accumulated memory usage (mb)')
ax[1].set_xlabel('Nodes count')
ax[1].grid()

plt.show()
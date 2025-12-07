from abc import ABC
from dataclasses import dataclass, asdict, field
import dataclasses
from typing import Protocol, runtime_checkable, Any
from types import MethodType


# ============================================================
#        INTERFACE — totalmente tipada, sem criar campos
# ============================================================

# @runtime_checkable
@dataclass
class ProcessorInterface(ABC):
    node: str = field(init=False)
    inputs: list[str] = field(init=False)
    routing: list[str] = field(init=False)

    def execute(self) -> Any:
        ...

@dataclass
class NodeProcessor:
    node: str
    inputs: list[str]
    routing: list[str]

    def execute(self) -> Any:
        raise NotImplementedError("Implement this method")

@dataclass
class PersonProcessor(ProcessorInterface):
    name: str
    age: int

    def execute(self) -> Any:
        return f"{self.name} is {self.age} years old, from node {self.node}"


# ============================================================
#                 EXEMPLO REAL DE USO
# ============================================================

n = NodeProcessor(node="node1", inputs=["John", "30"], routing=["node2", "node3"])
p = PersonProcessor(name="John", age=30)

# iterate dataclass fields
fn = set(n.name for n in dataclasses.fields(n))
fp = set(n.name for n in dataclasses.fields(p))

for f in fp - fn:
    # print(f)
    setattr(n, f, getattr(p, f))
# setattr(n, "execute", p.execute)
n.execute = MethodType(p.execute.__func__, n)

print([n.name for n in dataclasses.fields(n)])
print(n.name)
print(n.age)
print(n.execute())

from dataclasses import dataclass, field
from typing import Generic, TypeVar
from rich import print

T = TypeVar("T")

@dataclass
class SelfDict(Generic[T]):
    """Classe que permite que subclasses funcionem como dict[str, T]."""

    _store: dict[str, T] = field(default_factory=dict)

    def __getitem__(self, key: str) -> T:
        return self._store[key]

    def __setitem__(self, key: str, value: T):
        if not isinstance(value, self.__class__):
            raise TypeError(f"Value must be {self.__class__.__name__}")
        self._store[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._store

    @property
    def items(self):
        return self._store.items()

    @property
    def keys(self):
        return list(self._store.keys())

    @property
    def values(self):
        return list(self._store.values())
    

@dataclass
class NodeOutputExecution(SelfDict["NodeOutputExecution"]):
    name: str = 'default_name'
    result: int = 1234

@dataclass
class NodesExecution(SelfDict["NodesExecution"]):
    id: str = 'default_id'
    executed: NodeOutputExecution = field(default_factory=NodeOutputExecution)

@dataclass
class Node:
    id: str
    executions: NodesExecution

node = Node(id="a", executions=NodesExecution())

# Criar

# node.executions["a"] = NodesExecution()
node.executions["a"].executed['a'] = NodeOutputExecution()

# node.executions['b'] = NodesExecution()
# node.executions['b'].result = 30

# print(node.executions.values)
# print(node.executions.keys)

print(node.executions["a"])


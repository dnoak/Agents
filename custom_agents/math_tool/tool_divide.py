
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
from models.agent import Processor
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Classifier, Replicator, Tool

class ToolDivideOutput(Replicator):
    result: float

class ToolDivide(Tool):
    """a/b"""
    a: float = Field(description='a')
    b: float = Field(description='b')

    def tool(self) -> float:
        return self.a / self.b
        # return str({'raise_error': 'Function API is offline'})

class ToolSubractProcessor(Processor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        return {'result': llm['result']}

def tool_divide_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='user:linked',
        output_schema=ToolDivideOutput,
        llm=None,
        processor=ToolSubractProcessor(),
        num_workers=1,
    )
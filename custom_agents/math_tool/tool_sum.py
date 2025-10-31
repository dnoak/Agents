from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
from models.agent import Processor
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Classifier, Replicator, Tool

class ToolAddOutput(Replicator):
    result: float

class ToolAdd(Tool):
    """a+b"""
    a: float = Field(description='a')
    b: float = Field(description='b')

    def tool(self) -> float:
        # return self.a + self.b
        return str({'raise_error': 'Function API is offline'})

class ToolSumProcessor(Processor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        return {'result': llm['result']}
    
def tool_add_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='user:linked',
        output_schema=ToolSumOutput,
        llm=None,
        processor=ToolSumProcessor(),
        num_workers=1,
    )
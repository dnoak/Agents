from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
from models.agent import Processor
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Classifier, Replicator, Tool

class ResponseOutput(Replicator):
    response: float

class ResponseProcessor(Processor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        return {'response': llm['result']}
    
def response_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='user:linked',
        output_schema=ResponseOutput,
        llm=None,
        processor=ResponseProcessor(),
        num_workers=1,
    )
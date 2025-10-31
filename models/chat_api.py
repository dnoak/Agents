import time
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema
from typing import Literal, Optional

class Message(BaseModel):
    id: str
    content: dict
    role: Literal['user', 'user:linked', 'assistant', 'tool:step', 'tool:result', 'system'] 
    timestamp: SkipJsonSchema[float] = Field(
        default_factory=lambda: time.time(),
        exclude=True
    )

class Messages(BaseModel):
    id: str
    data: list[Message]
    source: SkipJsonSchema[None] = Field(
        default=None,
        exclude=True
    )
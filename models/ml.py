from abc import ABC, abstractmethod
from litellm.types.utils import ModelResponse, EmbeddingResponse
from src.instructions import LlmInstructions

class LlmModel(ABC):
    model_name: str

    # def format_messages(self, instructions: LlmInstructions, messages: list[dict]) -> list[dict]:
    #     dict_messages = [{'content': instructions.content, 'role': 'system'}]
    #     dict_messages += [
    #         {'content': h.format_content(), 'role': h.role} for h in messages[0].history
    #         if 'linked' not in h.role
    #     ]
    #     if 'linked' not in messages[0].role:
    #         content = MessagesFormatter(messages=messages).format()
    #         dict_messages += [{'content': content, 'role': messages[0].role}]
    #     return dict_messages

    @abstractmethod
    async def acomplete(self, **kwargs) -> ModelResponse: ...

    @abstractmethod
    def complete(self, **kwargs) -> ModelResponse: ...


class EmbeddingModel(ABC):
    model_name: str

    @abstractmethod
    async def aembed(self, **kwargs) -> EmbeddingResponse: ...

    @abstractmethod
    def embed(self, **kwargs) -> EmbeddingResponse: ...

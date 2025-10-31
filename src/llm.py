import asyncio
from dataclasses import dataclass, field
import json
import re
from litellm import completion, acompletion
from litellm.types.utils import ModelResponse
from litellm.cost_calculator import completion_cost
from termcolor import colored
from typing import Literal, Optional
from src.message import Messages
from src.instructions import LlmInstructions
from models.ml import LlmModel
from utils.json_parser import extract_json

@dataclass
class LLM:
    model: LlmModel
    instructions: LlmInstructions
    debug: bool = False

    def __post_init__(self):
        self.alocker = asyncio.Lock()

    def _debug(self, messages: list[dict], response: ModelResponse):
        if not self.debug: return
        debug_colors = {
            "system": "yellow",
            "assistant": "green",
            "user": "blue",
            'user:linked': 'grey',
        }
        # dict_messages = self.model.format_messages(self.instructions, messages)
        print(f"\n\n{colored(f'[{self.model.model_name}]', color='red', attrs=['bold'])}")
        for m in messages:
            print(colored(f"{m['role']}:\n", color=debug_colors[m['role']], attrs=['bold']), end='')
            print(colored(f"{m['content']}\n", color=debug_colors[m['role']]))
        print(f"{colored('[OUTPUT]:', color='green', attrs=['bold'])}")
        print(f"\n{colored(response.choices[0].message.content, color='green')}\n\n")
    
    def _update_costs_metadata(
            self, 
            messages: list[Messages], 
            response: ModelResponse,
            metadata: dict[str, list[dict]]
        ):
        assert all(m.id == messages[0].id for m in messages)
        if messages[0].id not in metadata:
            metadata[messages[0].id] = []
        # print('🔴 llm', completion_cost(completion_response=response))
        metadata[messages[0].id].append({
            'cost': completion_cost(completion_response=response),
            'model': self.model.model_name,
            'input_tokens': response.usage.prompt_tokens,
            'output_tokens': response.usage.completion_tokens,
        })

    async def _aupdate_costs_metadata(
            self, 
            messages: list[Messages], 
            response: ModelResponse,
            metadata: dict[str, list[dict]]
        ):
        async with self.alocker:
            self._update_costs_metadata(messages, response, metadata)
    
    def _format_response(self, response: ModelResponse) -> dict:
        content = response.choices[0].message.content
        try:
            json_content = extract_json(content)
        except Exception as e:
            print(content)
            raise ValueError(f'InvalidJsonError({e})')
        try:
            return self.instructions.output_schema(**json_content).model_dump(by_alias=True)
        except:
            print(content)
            raise Exception(
                colored(
                    f'\n❌ ❌ ❌ Schema validation failed for agent '
                    f'`{self.instructions.output_schema.__name__}`:\n{content}',
                    color='red', attrs=['bold']
                ))

    def complete(self):
        ...
    
    async def acomplete(
            self, id: str,
            messages: Messages,
            metadata: dict[str, list[dict]],
            roles_filter: dict[str, str] | Literal['basic', 'debug'] ,
        ) -> dict:
        response = await self.model.acomplete(
            instructions=self.instructions,
            messages=messages.to_llm(roles_filter=roles_filter),
        )
        if self.debug: self._debug(messages.to_llm(roles_filter=roles_filter), response)
        # await self._aupdate_costs_metadata(session_id, response, metadata)
        return self._format_response(response)


@dataclass
class LlmApi(LlmModel):
    model_name: str
    temperature: float = 1.0
    base_url: Optional[str] = None
    
    def complete(self):
        ...
    
    async def acomplete(self, instructions: LlmInstructions, messages: list[dict]) -> ModelResponse:
        # dict_messages = self.format_messages(instructions, messages)
        return await acompletion(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {'name': 'response', 'schema': instructions.output_schema.model_json_schema()}
            },
            base_url=self.base_url,
        ) # type: ignore

# @dataclass
# class FakeLlm(LlmModel):
#     model_name: str
#     temperature: float = 1.0
#     base_url: Optional[str] = None

#     def complete(self) -> ModelResponse: ...
#     def acomplete(self) -> ModelResponse: ...
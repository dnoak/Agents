import asyncio
from dataclasses import dataclass
from litellm import embedding, aembedding
from litellm.types.utils import EmbeddingResponse
from litellm.cost_calculator import completion_cost
from src.message import Message, MessagesFormatter
from models.ml import EmbeddingModel
from termcolor import colored

@dataclass
class Embedder:
    model: EmbeddingModel
    debug: bool = False

    def __post_init__(self):
        self.alocker = asyncio.Lock()

    def _debug(self, messages: list[Message], response: EmbeddingResponse):
        if not self.debug: return
        messages_str = '\n'.join([MessagesFormatter([m]).format() for m in messages])
        print(f"\n\n{colored(f'[{self.model.model_name}]', color='red', attrs=['bold'])}")
        print(f"{colored('text: ', color='blue', attrs=['bold'])}", end='')
        print(f"{colored(messages_str, color='blue')}")
        print(f"{colored('embedding: ', color='green', attrs=['bold'])}", end='')
        list_of_embeddings = list(map(lambda x: round(x, 3), response.data[0]['embedding']))
        print(f"{colored(f"{list_of_embeddings[:4] + ['...']}", color='green')}\n\n")

    def _update_costs_metadata(
            self, 
            messages: list[Message], 
            response: EmbeddingResponse,
            metadata: dict[str, list[dict]]
        ):
        assert all(m.id == messages[0].id for m in messages)
        if messages[0].id not in metadata:
            metadata[messages[0].id] = []
        metadata[messages[0].id].append({
            'cost': completion_cost(completion_response=response),
            'model': self.model.model_name,
            'input_tokens': response.usage.prompt_tokens,
            'output_tokens': response.usage.completion_tokens,
        })

    async def _aupdate_costs_metadata(
            self, 
            messages: list[Message], 
            response: EmbeddingResponse,
            metadata: dict[str, list[dict]]
        ):
        async with self.alocker:
            self._update_costs_metadata(messages, response, metadata)

    def _format_response(self, response: EmbeddingResponse) -> list[float]:
        return response.data[0]['embedding']

    def embed(self, messages: list[Message], metadata: dict[str, list[dict]]) -> list[float]:
        response = self.model.embed(
            messages='\n'.join([MessagesFormatter([m]).format() for m in messages])
        )
        self._debug(messages, response)
        self._update_costs_metadata(messages, response, metadata)
        return self._format_response(response)
    
    async def aembed(self, messages: list[Message], metadata: dict[str, list[dict]]) -> list[float]:
        response = await self.model.aembed(
            messages='\n'.join([MessagesFormatter([m]).format() for m in messages])
        )
        self._debug(messages, response)
        await self._aupdate_costs_metadata(messages, response, metadata)
        return self._format_response(response)


@dataclass
class EmbeddingApi(EmbeddingModel):
    model_name: str

    def embed(self, messages: list[str]) -> EmbeddingResponse:
        return embedding(
            model=self.model_name,
            input=messages
        )
    
    async def aembed(self, messages: list[str]) -> EmbeddingResponse:
        return await aembedding(
            model=self.model_name,
            input=messages
        )
        

if __name__ == '__main__':
    from src.message import Message

    messages = [
        Message(
            id='abc123',
            content={'input': 'carros economicos?'},
            history=[],
            role='user',
            source=None
        ),
        Message(
            id='abc123',
            content={'input': 'tubarao branco?'},
            history=[],
            role='user',
            source=None
        ),
    ]

    embedding_api = Embedder(
        model=EmbeddingApi(model_name='text-embedding-3-small'),
        debug=True
    )

    metadata = {}
    async def main ():
        embedding_api.embed(messages, metadata)

    asyncio.run(main())
    print(metadata)
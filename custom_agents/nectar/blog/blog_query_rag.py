from dataclasses import dataclass
from pydantic import Field
import requests
import os
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.embedder import Embedder, EmbeddingApi
from src.message import Message
from src.agent import Agent
from models.agent import Replicator, Processor
from db.nectar.elastic import ElasticNectarBlog

class BlogQueryLlmOutput(Replicator):
    formatted_user_input: str = Field(
        description="Pergunta do usuário com correções gramaticais"
    )
    keywords: list[str] = Field(
        description="Palavras-chave da pergunta do usuário - Use apenas palavras-chaves relevantes para uma busca de proximidade de palavras em um banco de dados de texto. Escreva corretamente seguindo a norma gramatical, mesmo que o usuário não tenha escrito corretamente. Não use mais de 5 palavras-chave."
    )
    date_start: str | None = Field(
        description="Caso haja alguma informação implícita ou explícita de data de início no contexto da pergunta. Escreva no formato YYYY-MM-DD."
    )
    date_end: str | None = Field(
        description="Caso haja alguma informação implícita ou explícita de data de fim no contexto da pergunta. Escreva no formato YYYY-MM-DD."
    )

class BlogRagOutput(Replicator):
    rag_output: str = Field(
        description="Resposta para o usuário"
    )

@dataclass
class BlogRagProcessor(Processor):
    def __post_init__(self):
        self.embedder = Embedder(
            model=EmbeddingApi(model_name='text-embedding-3-small'),
            debug=True
        )
        self.blog: ElasticNectarBlog = ElasticNectarBlog(
            index='nectar_blog',
            hosts=os.environ['ELASTIC_HOST'],
            basic_auth=(os.environ['ELASTIC_USER'], os.environ['ELASTIC_PASSWORD']),
            verify_certs=False,
        )

    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        formatted_user_input: str = llm['formatted_user_input']
        keywords: list[str] = llm['keywords']
        date_start: str = llm['date_start']
        date_end: str = llm['date_end']
        
        messages = [messages[0]] # mocked message object
        messages[0].content = {'...': formatted_user_input}

        rag_result = self.blog.search(
            query_text=formatted_user_input,
            query_vector=self.embedder.embed(messages, agent.metadata), 
            size=5
        )
        return {
            'rag_output': self.blog.format_search_result(rag_result)
        }

def blog_query_rag_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='user',
        output_schema=BlogRagOutput,
        llm=LLM(
            model=LlmApi(model_name='gpt-4o-mini'),
            instructions=LlmInstructions(
                background='Você é um assistente de uma plataforma de CRM que monta uma query para um banco de dados de texto (ElasticSearch). Você escreverá a query no formato JSON.',
                reasoning=True,
                steps=[
                    'Caso haja informação de apenas a data de início ou apenas a data de fim, preencha com a data somente o campo da data referente ao contexto da pergunta.',
                    'Preencher apenas o campo `date_start` significa "a partir de `date_start`", e preencher apenas o campo `date_end` significa "até `date_end`".',
                    'Preste atenção a contextos onde implicitamente existe uma data de início e de fim ao mesmo tempo, por exemplo quando se cita o mês, ou algum período que geralmente é definido como "de X até Y".',
                ],
                output_schema=BlogQueryLlmOutput
            ),
            debug=debug
        ),
        processor=BlogRagProcessor(),
        num_workers=4,
    )

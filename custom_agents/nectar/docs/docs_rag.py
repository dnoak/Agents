from dataclasses import dataclass
import os
import random
from typing import Optional
import graphviz
import openai
from pydantic import Field
from src.prompts import SystemPrompt
from src.agent import Agent
from src.llm.gpt import GptLlmApi
from models.agent import Replicator, Classifier, AgentProcessor
from db.nectar.elastic import ElasticNectarBlog

class BlogRagOutput(Replicator):
    user_input: str = Field(
        description="Pergunta do usuário"
    )
    rag_output: str = Field(
        description="Resposta para o usuário"
    )

@dataclass
class BlogRagProcessor(AgentProcessor):
    def __post_init__(self):
        openai.api_key = os.environ['OPENAI_API_KEY']
        self.blog: ElasticNectarBlog = ElasticNectarBlog(
            index='nectar_blog',
            hosts=os.environ['ELASTIC_HOST'],
            basic_auth=(os.environ['ELASTIC_USER'], os.environ['ELASTIC_PASSWORD']),
            verify_certs=False,
        )

    def embed(self, text: str) -> list[float]:
        return openai.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        ).data[0].embedding

    def process(self, agent: Agent, input_args: dict, llm_output: dict | None) -> dict:
        user_input = input_args['input'].contents[0]['user_input']
        keywords: list[str] = input_args['input'].contents[0]['keywords']
        date_start: str = input_args['input'].contents[0]['date_start']
        date_end: str = input_args['input'].contents[0]['date_end']

        rag_result = self.blog.search(
            query_text=user_input, 
            query_vector=self.embed(user_input), 
            size=7
        )
        return {
            'user_input': user_input,
            'rag_output': self.blog.format_search_result(rag_result)
        }

def docs_rag_fn(name: str, debug: dict):
    return Agent(
        name=name,
        role='user:connection',
        output_schema=BlogRagOutput,
        processor=BlogRagProcessor(),
        debug=debug
    )

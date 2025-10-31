from dataclasses import dataclass
import random
from typing import Optional
import graphviz
from pydantic import Field
from src.prompts import SystemPrompt
from src.agent import Agent
from src.llm.gpt import GptLlmApi
from models.agent import Replicator, Classifier, AgentProcessor

class BlogQueryOutput(Replicator):
    user_input: str = Field(
        description="Pergunta do usuário (a exata pergunta que o usuário fez)"
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

blog_query_prompt = SystemPrompt(
    background='Você é um assistente de uma plataforma de CRM que monta uma query para um banco de dados de texto (ElasticSearch). Você escreverá a query no formato JSON.',
    reasoning=True,
    steps=[
        'Caso haja informação de apenas a data de início ou apenas a data de fim, preencha com a data somente o campo da data referente ao contexto da pergunta.',
        'Preencher apenas o campo `date_start` significa "a partir de `date_start`", e preencher apenas o campo `date_end` significa "até `date_end`".',
        'Preste atenção a contextos onde implicitamente existe uma data de início e de fim ao mesmo tempo, por exemplo quando se cita o mês, ou algum período que geralmente é definido como "de X até Y".',
    ],
    output_schema=BlogQueryOutput
)

def docs_query_fn(name: str, debug: dict):
    return Agent(
        name=name,
        instructions=blog_query_prompt,
        llm_model=GptLlmApi(model_name='gpt-4o-mini'),
        role='user:connection',
        output_schema=BlogQueryOutput,
        debug=debug
    )

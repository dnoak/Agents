from dataclasses import dataclass
import os
import random
from typing import Optional
from pydantic import Field
from src.instructions import LlmInstructions
from src.agent import Agent
from src.llm import LLM, LlmApi
from src.message import Message
from models.agent import Replicator, Classifier, Processor
import requests
import time

class BlogResponseLlmOutput(Replicator):
    response: str = Field(
        description="Resposta formatada para o usuário." 
    )
    references: list[str] | None = Field(
        description="Aqui você vai escrever os títulos dos artigos consultados para responder a pergunta, caso haja algum. Não repita o título do artigo caso ele apareça mais de uma vez."
    )

class BlogResponseOutput(Replicator):
    response: str = Field(
        description="Resposta para o usuário." 
    )

class BlogResponseProcessor(Processor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        formatted_response = f"{llm['response']}"
        if llm['references']:
            formatted_response += f"\n\nFontes:\n"
            for reference in llm['references']:
                formatted_response += f" - {reference}\n"
        return {'response': formatted_response}


def blog_response_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='assistant',
        output_schema=BlogResponseOutput,
        llm=LLM(
            model=LlmApi(model_name='gpt-4o-mini'),
            instructions=LlmInstructions(
                background='Você é um assistente de uma plataforma de CRM que recebe resultados de um RAG (Retrieval Augmented Generation) e responde cordialmente para o usuário. Você deve fazer uma analise dos fragmentos de textos do RAG e decidir se eles têm a resposta para o usuário. Você deverá escrever a resposta no formato JSON.',
                reasoning=True,
                steps=[
                    'Você vai resceber a pergunta do usuário e em seguida vai receber uma lista ranqueada (com base na busca do usuário) de fragmentos do texto de artigos sobre CRM, cada um com o seu título.',
                    'Podem vir mais de um fragmento do mesmo artigo, mas não necessariamente em ordem, e os fragmentos podem conter informações parciais ou não-relevantes.',
                    'Caso os fragmentos sejam suficientes para responder o usuário, escreva a resposta com o máximo de detalhes possível extraído do resultado do RAG, considerando o contexto da pergunta dele.',
                    'Se o fragmento ou título fizer parte de um artigo referente a pergunta, mas não explicar suficientemente o assunto (ex.: introduções, informações parciais, final de artigo, etc), cite as referências e informe ao usuário que ele pode consultar o artigo completo para mais detalhes.',
                    'Caso não haja respostas relevantes e nem títulos que façam parte do contexto da pergunta, escreva que não foi achada nenhuma resposta, não dê as referências, e sugira dicas para o usuário tentar fazer a mesma pergunta usando outros termos ou palavras-chaves',
                ],
                output_schema=BlogResponseLlmOutput
            ),
            debug=debug
        ),
        processor=BlogResponseProcessor(),
        num_workers=4,
    )
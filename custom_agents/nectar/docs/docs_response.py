from dataclasses import dataclass
import random
from typing import Optional
import graphviz
from pydantic import Field
from src.prompts import SystemPrompt
from src.agent import Agent
from src.llm.gpt import GptLlmApi
from models.agent import Replicator, Classifier, AgentProcessor

class BlogResponseOutput(Replicator):
    response: str = Field(
        description="Resposta formatada para o usuário." 
    )
    references: list[str] | None = Field(
        description="Aqui você vai escrever os títulos dos artigos consultados para responder a pergunta, caso haja algum. Não repita o título do artigo caso ele apareça mais de uma vez."
    )

blog_response_prompt = SystemPrompt(
    background='Você é um assistente de uma plataforma de CRM que recebe resultados de um RAG (Retrieval Augmented Generation) e responde cordialmente para o usuário. Você deve fazer uma analise dos fragmentos de textos do RAG e decidir se eles têm a resposta para o usuário. Você deverá escrever a resposta no formato JSON.',
    reasoning=True,
    steps=[
        'Você vai resceber a pergunta do usuário e em seguida vai receber uma lista ranqueada (com base na busca do usuário) de fragmentos do texto de artigos sobre CRM, cada um com o seu título.',
        'Podem vir mais de um fragmento do mesmo artigo, mas não necessariamente em ordem, e os fragmentos podem conter informações parciais ou não-relevantes.',
        'Caso os fragmentos sejam suficientes para responder o usuário, escreva a resposta com o máximo de detalhes possível extraído do resultado do RAG, considerando o contexto da pergunta dele.',
        'Se o fragmento ou título fizer parte de um artigo referente a pergunta, mas não explicar suficientemente o assunto (ex.: introduções, informações parciais, final de artigo, etc), cite as referências e informe ao usuário que ele pode consultar o artigo completo para mais detalhes.',
        'Caso não haja respostas relevantes e nem títulos que façam parte do contexto da pergunta, escreva que não foi achada nenhuma resposta, não dê as referências, e sugira dicas para o usuário tentar fazer a mesma pergunta usando outros termos ou palavras-chaves',
    ],
    output_schema=BlogResponseOutput
)

def docs_response_fn(name: str, debug: dict):
    return Agent(
        name=name,
        instructions=blog_response_prompt,
        llm_model=GptLlmApi(model_name='gpt-4o-mini'),
        role='assistant',
        output_schema=BlogResponseOutput,
        debug=debug
    )

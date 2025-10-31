import os
from pydantic import Field, model_validator
import requests
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Replicator, Processor

class OutOfScopeOutput(Replicator):
    response: str = Field(
        description="Resposta para o usuário." 
    )

def out_of_scope_response_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='assistant',
        output_schema=OutOfScopeOutput,
        llm=LLM(
            model=LlmApi(model_name='gpt-4o-mini'),
            instructions=LlmInstructions(
                background='Você é um assistente de uma plataforma de CRM que responderá que a pergunta ou interação do usuário está fora do escopo. Responda no formato JSON.',
                reasoning=False,
                steps=[
                    'Caso a pergunta do usuário seja educada e legítima, responda que a pergunta dele não faz parte do escopo do atendimento da plataforma de CRM e diga para ele perguntar algo relacionado ao tema',
                    'Caso a pergunta seja ofensiva ou não educada, responda apenas "💀..."'  
                ],
                output_schema=OutOfScopeOutput
            ),
            debug=debug
        ),
        num_workers=4,
    )

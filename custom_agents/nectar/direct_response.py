import os
from pydantic import Field, model_validator
import requests
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Replicator, Processor

class DirectResponseOutput(Replicator):
    response: str = Field(
        description="Resposta para o usuário" 
    )

def direct_response_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='user',
        output_schema=DirectResponseOutput,
        llm=LLM(
            model=LlmApi(model_name='gpt-4o-mini'),
            instructions=LlmInstructions(
                background='Você é um assistente de uma plataforma de CRM e receberá a interação do usuário, que pode ser uma simples saudação ou perguntas básicas sobre CRM. Você responderá essa interação no formato JSON.',
                reasoning=False,
                steps=[
                    'No final de cada resposta, analise o contexto das interações e, **CASO NECESSÁRIO**, acrescente na resposta uma pergunta se o usuário ainda tem alguma dúvida.',
                ],
                output_schema=DirectResponseOutput
            ),
            debug=debug
        ),
        num_workers=4,
    )

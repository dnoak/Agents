from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Classifier

class HomeAutomationClassifierOutput(Classifier):
    direct_response: Optional[bool] = Field(
        description="Resposta direta sem necessidade de controle de dispositivos. Escolher quando o usuário fizer perguntas gerais que não envolvem alguma operação física na casa. Exemplo: 'Como funciona um sensor de movimento?', 'O que é automação residencial?', 'Qual a melhor assistente de voz para casa inteligente?'."
    )
    light_control: Optional[bool] = Field(
        description="Controle de iluminação da casa. Escolher quando o usuário solicitar ações relacionadas a ligar, desligar ou ajustar luzes. Exemplo: 'Acenda as luzes da sala', 'Diminua a intensidade das luzes do quarto', 'Desligue todas as luzes'."
    )
    clock_control: Optional[bool] = Field(
        description="Configuração de alarmes e notificações. Escolher quando o usuário solicitar a ativação de alarmes de segurança ou lembretes para ações futuras. Exemplo: 'Ative o alarme de segurança', 'Me lembre de fechar as janelas às 20h', 'Desative o alarme da garagem'."
    )
    temperature_control: Optional[bool] = Field(
        description="Controle de temperatura e climatização. Escolher quando o usuário solicitar ajustes no termostato ou ar-condicionado. Exemplo: 'Ajuste a temperatura para 22 graus', 'Ligue o ar-condicionado da sala', 'Desligue o aquecedor'."
    )
    climate_info: Optional[bool] = Field(
        description="Informações sobre o clima. Escolher quando o usuário solicitar informações sobre o clima atual ou previsão. Exemplo: 'Qual é o tempo de chuva?', 'Qual é a previsão do tempo de sol?', 'Qual é o vento?'."
    )

def home_automation_classifier_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='user:linked',
        output_schema=HomeAutomationClassifierOutput,
        llm=LLM(
            model=LlmApi(model_name='gpt-4o-mini'),
            instructions=LlmInstructions(
                background='Você é um classificador de comandos para um assistente de automação residencial. Você receberá um comando do usuário e deverá escolher as opções para classificar o tipo de ação necessária. Você sempre deve responder no formato JSON.',
                tools=None,
                reasoning=True,
                steps=[
                    'Escolha as opções que melhor se adequam ao comando do usuário com base no contexto da automação residencial.',
                ],
                output_schema=HomeAutomationClassifierOutput
            ),
            debug=debug
        ),
        num_workers=1,
    )
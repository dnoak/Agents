from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Classifier

class Light(BaseModel):
    """Representa o estado de uma luz em um ambiente."""
    brightness: Optional[int] = Field(
        description="Intensidade da luz, de 0 (desligada) a 100 (brilho máximo)."
    )
    color: Optional[Literal['white', 'red', 'green', 'blue']] = Field(
        description="Cor da luz."
    )

class LightControlOutput(Classifier):
    """Estrutura de classificação para controle de iluminação de diferentes cômodos."""
    tv_room_lights: Optional[Light] = Field(
        description="Controle de iluminação da sala de TV."
    )
    guest_room_lights: Optional[Light] = Field(
        description="Controle de iluminação do quarto de visitas."
    )
    master_bedroom_lights: Optional[Light] = Field(
        description="Controle de iluminação do quarto principal (suíte)."
    )

def light_control_fn(name: str, debug: bool = False) -> Agent:
    """Cria um agente de IA para classificar comandos de controle de iluminação."""
    return Agent(
        name=name,
        role='user:linked',
        output_schema=LightControlOutput,
        llm=LLM(
            model=LlmApi(model_name='gpt-4o-mini'),
            instructions=LlmInstructions(
                background="Você é um classificador de comandos para um assistente de automação residencial focado em controle de iluminação. Seu objetivo é interpretar comandos do usuário e classificar a ação necessária de acordo com os cômodos e parâmetros disponíveis. Sempre responda no formato JSON.",
                tools=None,
                reasoning=True,
                steps=[
                    "Identifique os cômodos mencionados no comando do usuário.",
                    "Altere apenas os cômodos que o usuário solicitou, e não responda sobre os demais cômodos.",
                    "Caso o usuário não seja específico sobre os detalhes da luz, apenas ligue ou desligue ela (0 ou 100 para brilho) e a cor sempre será branca.",
                    "Caso o comando seja genérico e não especifique um cômodo em especial, faça o comando para todos os cômodos disponíveis.",
                ],
                output_schema=LightControlOutput
            ),
            debug=debug
        ),
        num_workers=1,
    )

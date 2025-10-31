from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
from models.agent import Processor
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Classifier, Replicator, Tool

class ClimateInfoLlmOutput(Classifier):
    task_done: bool = Field(
        description='Aqui você vai marcar quando a sua tarefa estiver concluída e você tiver toda a resposta para o usuário'
    )
    response_pipeline: str = Field(
        description='Aqui você vai marcar a tarefa que você está fazendo agora, em seguida deve descrever o próximo passo (caso necessário)'   
    )
    tools: Optional[list[dict[str, dict]]] = Field(
        description='Ferramentas que serão utilizadas para a tarefa, escreva o nome da ferramenta e os argumentos delas'
    )

class ExternalClimateTool(Tool):
    city: str = Field(
        description="Cidade onde será feita a pesquisa do clima"
    )
    date: str = Field(
        description="Data perguntada pelo usuário, formate como DD/MM/AAAA HH:MM"
    )
    variables: Literal['temperature'] = Field(
        description='Variáveis escolhidas pelo usuário'
    )

    def tool(self):
        return {'ExternalClimateTool': '25°C'}

class InternalClimateTool(Tool):
    room: str = Field(
        description='Local da casa'
    )
    variables: Literal['temperature'] = Field(
        description='Variáveis escolhidas pelo usuário'
    )

    def tool(self):
        return {'InternalClimateTool': '20°C'}

class ClimateInfoOutput(Classifier):
    climate_response_response: Optional[bool] = Field(
        description="Resposta para o usuário sobre o clima"
    )
    climate_info: Optional[bool] = Field(
        description="Informações sobre o clima"
    )

class ClimateInfoProcessor(Processor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict | None:
        # fake climate api
        if llm['task_done'] is True:
            return {'ready_response': True, 'climate_info': False}
        return {'ready_response': False, 'climate_info': True}


def climate_info_fn(name: str, debug: bool = False):
    return Agent(
        name=name,
        role='user:linked',
        output_schema=ClimateInfoOutput,
        llm=LLM(
            model=LlmApi(model_name='gpt-4o-mini'),
            instructions=LlmInstructions(
                background='Você é um assistente de automação residencial focado em informações sobre o clima. Seu objetivo é interpretar comandos do usuário e classificar a ação necessária de acordo com os cômodos e parâmetros disponíveis. Sempre responda no formato JSON.',
                tools=[ExternalClimateTool, InternalClimateTool],
                reasoning=True,
                steps=[
                    'Você tem a opção de usar as `tools` caso precise uma consulta externa',
                    'Use as tools até cumprir o seu objetivo de responder o usuário'
                ],
                output_schema=ClimateInfoLlmOutput
            ),
            debug=debug
        ),
        num_workers=1,
    )
from dataclasses import dataclass
from typing import Literal, Optional
from pydantic import BaseModel, Field
from models.agent import Tool
from rich import print

class LightControl(Tool):
    """
    Controle geral das luzes dos cômodos. 
    """
    room: str = Field(
        description='Cômodo da casa no qual a lâmpada está.'
    )
    light_id: int = Field(
        description='Identificador da lâmpada no cômodo.'
    )
    brightness: Optional[int] = Field(
        default=None,
        description='Controla a intensidade da luz da lâmpada. 0 para desligado, 100 para brilho total.',
        ge=0,
        le=100
    )
    color: Optional[Literal['white', 'yellow', 'blue', 'green', 'red']] = Field(
        default=None,
        description='Cor da luz da lâmpada.'
    )

    def tool(self) -> None:
        print(f'💡 Luz do cômodo {self.room}:{self.light_id}:')
        print(f'    cor: {self.color}')
        print(f'    brilho: {self.brightness}/100')


class AirConditionerControl(Tool):
    """
    Controle geral dos ar condicionados.
    """
    room: Optional[str] = Field(
        default=None,
        description='Cômodo da casa no qual o ar condicionado está.'
    )
    air_conditioner_id: Optional[int] = Field(
        default=None,
        description='Identificador do ar condicionado no cômodo.'
    )
    temperature: Optional[int] = Field(
        default=None,
        description='Controla a temperatura do ar condicionado.'
    )

    def tool(self) -> None:
        print(f'💨 Ar condicionado do cômodo {self.room}:{self.air_conditioner_id}:')
        print(f'    temperatura: {self.temperature}/100')


class TvRemoteControlControl(Tool):
    """
    Controle remoto universal das TVs da casa.
    """
    room: str = Field(
        description='Cômodo da casa no qual o controle remoto está.'
    )
    tv_id: int = Field(
        description='Identificador da TV no cômodo.'
    )
    on_off: Optional[Literal['on', 'off']] = Field(
        default=None,
        description='Liga ou desliga a TV.'
    )
    volume: Optional[int] = Field(
        default=None,
        description='Controla o volume da TV.',
        ge=0,
        le=100
    )
    channel: Optional[int] = Field(
        default=None,
        description='Troca o canal da TV.',
    )

    def tool(self) -> None:
        print(f'📺 TV do cômodo {self.room}:{self.tv_id}:')
        print(f'    ligado: {self.on_off}')
        print(f'    volume: {self.volume}/100')
        print(f'    canal: {self.channel}')

class TriggerInterval(BaseModel):
    """
    Intervalo de tempo entre as disparos das ferramentas.
    """
    seconds: int = Field(
        description='Tempo em segundos entre as disparos das ferramentas.'
    )
    minutes: int = Field(
        description='Tempo em minutos entre as disparos das ferramentas.'
    )
    hours: int = Field(
        description='Tempo em horas entre as disparos das ferramentas.'
    )

class SmartHomeTrigger(Tool):
    """
    Gatilho para disparar automaticamente os dispositivos da smart home.
    """
    target: Tool = Field(
        description='Ferramenta que devem ser disparadas.'
    )
    trigger_function_call: str = Field(
        description='Chamada da função que dispara a ferramenta.'
    )
    trigger_interval: TriggerInterval = Field(
        description='Intervalo de tempo entre as disparos das ferramentas.'
    )

    def tool(self) -> None:
        print(f'🔫 Gatilho para disparar a ferramenta {self.target.__name__}:')
        print(f'    chamada: {self.trigger_function_call}')
        print(f'    intervalo: {self.trigger_interval.model_dump()}')
    
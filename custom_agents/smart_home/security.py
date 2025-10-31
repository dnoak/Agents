from dataclasses import dataclass
import random
from typing import Literal, Optional
from pydantic import BaseModel, Field
from models.agent import Tool
from rich import print

class __shared__(BaseModel):
    description: str = 'Ferramentas de monitoramento e controle de segurança.'
    keywords: list[str] = [
        'segurança',
        'monitoramento',
        'vigilância',
        'controle',
        'alertas',
    ]

class CameraMonitoring(Tool):
    """
    Analisa a imagem momentânea de uma câmera de segurança.
    """
    location: str = Field(
        description="Localização da câmera (ex: entrada principal, garagem, etc.)."
    )
    camera_id: int = Field(
        description="Identificador da câmera de segurança."
    )

    class Metadata:
        description = __shared__().description
        keywords = __shared__().keywords + ['câmera', 'imagem']

    def tool(self) -> None:
        print(f'📷 Câmera de segurança {self.location}:')
        print(f'    ID da câmera: {self.camera_id}')
        print(f'    análise: {random.choice(["✅ Nada suspeito detectado", "❌ Um ladrão está roubando a casa!!"])}')


class ElectricFenceStatus(Tool):
    """
    Checa o status da cerca elétrica para segurança.
    """
    location: str = Field(
        description="Localização da cerca (ex: perímetro do jardim, entrada)."
    )
    fence_id: int = Field(
        description="Identificador da cerca elétrica."
    )

    def tool(self) -> None:
        print(f'⚡ Cerca elétrica na {self.location}:')
        print(f'    ID da cerca: {self.fence_id}')
        print(f'    Estado: {random.choice(["on", "off"])}')

class MotionSensorStatus(Tool):
    """
    Monitoramento de sensores de movimento para detectar intrusos.
    """
    location: str = Field(
        description="Localização do sensor (ex: corredor, área externa, etc.)."
    )
    sensor_id: int = Field(
        description="Identificador do sensor de movimento."
    )
    check_interval_seconds: Optional[int] = Field(
        description="Verifica se houve alguma movimentação durante esse intervalo de tempo.",
        default=5,
    )

    def tool(self) -> None:
        print(f'🚨 Sensor de movimento em {self.location}:')
        print(f'    ID do sensor: {self.sensor_id}')
        print(f'    Movimento detectado em {self.check_interval_seconds}: {random.choice(["✅ Não", "❌ Sim"])}')

class AlarmSystem(Tool):
    """
    Sistema de alarmes de segurança para a casa.
    """
    location: str = Field(
        description="Localização do sistema de alarme (ex: entrada principal, perímetro)."
    )
    status: Optional[Literal['armed', 'disarmed']] = Field(
        default=None,
        description="Estado do alarme (armado ou desarmado)."
    )
    test_mode: Optional[bool] = Field(
        default=False,
        description="Ativa o alarme no modo teste, dispara apenas a sirene, sem usar as medidas de segurança."
    )

    def tool(self) -> None:
        print(f'🚨 Sistema de alarme na {self.location}:')
        print(f'    Estado: {self.status}')
        print(f'    Modo teste: {self.test_mode}')


class DoorbellStatus(Tool):
    """
    Campainha inteligente com câmera integrada.
    """
    doorbell_id: int = Field(
        description="Identificador da campainha."
    )
    location: str = Field(
        description="Localização da campainha (ex: entrada principal, portão)."
    )

    def tool(self) -> None:
        print(f'🔔 Campainha na {self.location}:')
        print(f'    ID da campainha: {self.doorbell_id}')
        print(f'    Visitante detectado: {random.choice(["✅ Não", "❌ Sim"])}')


class SmartLock(Tool):
    """
    Controle de fechaduras inteligentes.
    """
    lock_id: int = Field(
        description="Identificador da fechadura inteligente."
    )
    location: str = Field(
        description="Localização da fechadura (ex: porta da frente, garagem, etc.)."
    )
    set_status: Optional[Literal['locked', 'unlocked']] = Field(
        description="Estado da fechadura (trancada ou destrancada)."
    )

    def tool(self) -> None:
        print(f'🔒 Fechadura inteligente na {self.location}:')
        print(f'    ID da fechadura: {self.lock_id}')
        print(f'    Estado anterior: {random.choice(["locked", "unlocked"])}')
        print(f'    Estado definido: {self.set_status}')


if __name__ == '__main__':
    cm = CameraMonitoring(location='entrada principal', camera_id=1)
    print(cm.Metadata.keywords)
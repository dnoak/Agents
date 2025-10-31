from dataclasses import dataclass
from typing import Literal, Optional
from pydantic import BaseModel, Field
from models.agent import Tool
from rich import print

class CurrentWeather(Tool):
    """
    Consulta as condições climáticas atuais para uma localização específica.
    """
    location: str = Field(
        description='Nome da cidade ou coordenadas geográficas para consulta do clima.'
    )
    
    def tool(self) -> None:
        print(f'☁️ Clima atual em {self.location}:')
        print(f'    (Aqui viria a resposta da API de clima)')


class WeatherForecast(Tool):
    """
    Obtém a previsão do tempo para os próximos dias em uma determinada localização.
    """
    location: str = Field(
        description='Nome da cidade ou coordenadas geográficas para previsão do tempo.'
    )
    days: Optional[int] = Field(
        default=3,
        description='Número de dias para previsão (padrão: 3 dias).',
        ge=1,
        le=14
    )
    
    def tool(self) -> None:
        print(f'📅 Previsão do tempo para {self.location} nos próximos {self.days} dias:')
        print(f'    (Aqui viria a resposta da API de clima)')


class AirQuality(Tool):
    """
    Obtém informações sobre a qualidade do ar para uma localização específica.
    """
    location: str = Field(
        description='Nome da cidade ou coordenadas geográficas para consulta da qualidade do ar.'
    )
    
    def tool(self) -> None:
        print(f'🌫️ Qualidade do ar em {self.location}:')
        print(f'    (Aqui viria a resposta da API de qualidade do ar)')


class UVIndex(Tool):
    """
    Obtém o índice de radiação UV para uma determinada localização.
    """
    location: str = Field(
        description='Nome da cidade ou coordenadas geográficas para consulta do índice UV.'
    )
    
    def tool(self) -> None:
        print(f'☀️ Índice UV em {self.location}:')
        print(f'    (Aqui viria a resposta da API de clima)')


class WeatherAlerts(Tool):
    """
    Obtém alertas climáticos para uma determinada região.
    """
    location: str = Field(
        description='Nome da cidade ou coordenadas geográficas para consulta de alertas climáticos.'
    )
    
    def tool(self) -> None:
        print(f'⚠️ Alertas climáticos para {self.location}:')
        print(f'    (Aqui viria a resposta da API de clima)')

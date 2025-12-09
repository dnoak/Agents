from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
import dotenv
import os

dotenv.load_dotenv()

class BaseSettings(PydanticBaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

class FastApiSettings(BaseSettings):
    host: str
    port: int
    model_config = SettingsConfigDict(env_prefix='FASTAPI_')

class McpSettings(BaseSettings):
    host: str
    port: int
    model_config = SettingsConfigDict(env_prefix='MCP_')

class RedisSettings(BaseSettings):
    host: str
    port: int
    keys_index: int
    values_index: int
    memory_index: int
    model_config = SettingsConfigDict(env_prefix='REDIS_')

class ElasticsearchSettings(BaseSettings):
    host: str
    port: int
    user: str
    password: str
    model_config = SettingsConfigDict(env_prefix='ELASTICSEARCH_')

class PostgresSettings(BaseSettings):
    host: str
    user: str
    password: str
    db: str
    port: int
    model_config = SettingsConfigDict(env_prefix='POSTGRES_')

class LlmSettings(BaseSettings):
    openai_api_key: str
    gemini_api_key: str
    model_config = SettingsConfigDict(env_prefix='LLM_')

class Settings(BaseSettings, case_sensitive=False):
    fastapi: FastApiSettings = FastApiSettings()
    mcp: McpSettings = McpSettings()
    redis: RedisSettings = RedisSettings()
    elasticsearch: ElasticsearchSettings = ElasticsearchSettings()
    postgres: PostgresSettings = PostgresSettings()
    llm: LlmSettings = LlmSettings()

settings = Settings()
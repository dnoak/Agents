from typing import Any
import langchain
from langchain.agents import create_agent
from pydantic import BaseModel
from rich import print

class ToolOutput(BaseModel):
    tool_name: str
    tool_result: Any

class AgentOutput(BaseModel):
    your_output_text: str
    used_tools: list[ToolOutput]

def test_tool():
    'teste'
    return 'Hello world!'

def test_tool2():
    'teste'
    return 'olá mundo!'

def test_tool3():
    'teste'
    return '你好世界！'

agent = create_agent(
    model="gpt-5-mini",
    tools=[test_tool, test_tool2, test_tool3],
    system_prompt="Teste todas as suas tools e me diga os resultados",
    response_format=AgentOutput,
)

print(agent.invoke(input={"messages": "olá mundo!"}))
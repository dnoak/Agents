import asyncio
from typing import Optional
import graphviz
from pydantic import Field, model_validator
from src.instructions import LlmInstructions
from src.llm import LLM, LlmApi
from src.message import Message
from src.agent import Agent
from models.agent import Replicator, Classifier, AgentProcessor

class InputClassifierOutput(Replicator):
    direct_response: bool = Field(
        description="Resposta direta sem consulta externa. Escolher quando o usuário perguntar coisas triviais sobre o CRM, informações de conhecimento geral, saudações de boas vindas ou despedidas. Exemplo: 'Olá, tudo bem?', 'Como vai você hoje?', 'para que serve o CRM?', 'qual o significado de CRM?', etc.",
    )
    blog_query: bool = Field(
        description="Blog que contém informações, dicas e estratégias dentro do contexto do CRM. Escolher quando o usuário falar sobre assuntos relacionados a perguntas um pouco mais técnicas sobre estratégias no CRM, dicas de vendas, prospecção de clientes, etc. Exemplo: 'como organizar eficientemente uma pipeline de vendas?', 'qual é o melhor CRM para vendas?', etc."
    )
    docs_query: bool = Field(
        description="Busca no banco de dados de documentos técnicos da plataforma do CRM. Escolher quando o usuário falar sobre assuntos técnicos, dúvidas e problemas relacionados a plataforma em si do CRM. Exemplo: 'como cadastrar um cliente?', 'onde posso encontrar inserir um email na pipeline de vendas?', 'como integrar o whatsapp com o CRM?', etc."
    )
    out_of_scope: bool = Field(
        description="Assunto fora de contexto. Escolher quando o usuário falar sobre assuntos que claramente não estão relacionados sobre o CRM ou perguntas sobre temas aleatórios. Exemplo: 'Qual o carro mais econômico em estradas?', 'Como ganhar dinheiro na bolsa de valores?', etc." 
    )

    @model_validator(mode='after')
    def chek_only_one_field_true(self):
        attributes = [getattr(self, attr) for attr in self.model_fields.keys()]
        assert all(isinstance(attr, bool) for attr in attributes)
        if sum(attributes) != 1:
            raise ValueError(f"At least one field must be true in {self.__class__.__name__}")
        return self

class AgentOutput(Classifier):
    output_processed: bool = Field(description="d1 processado")
    
class Processor(AgentProcessor):
    def process(self, agent: Agent, messages: list[Message], llm: dict) -> dict:
        output = {'output_processed': True}
        return output

agent = Agent(
    name='agente_exemplo',
    role='assistant',
    output_schema=AgentOutput,
    llm=LLM(
        model=LlmApi(model_name='gpt-4o-mini', debug=True),
        instructions=LlmInstructions(
            background='Você é um classificador de interações de um usuário numa plataforma de CRM. Você receberá a interação do usuário e deverá escolher **APENAS UMA** das opções para classificar o tipo de resposta. Você sempre deve responder no formato JSON.',
            reasoning=True,
            steps=[
                'Escolha a opção que melhor se adequa ao tipo de resposta do usuário de acordo com o contexto da conversa',
                'Preencha **APENAS UM** dos campos como `true`, e **TODOS OS DEMAIS** campos com `false`',
            ],
            output_schema=InputClassifierOutput
        ),
    ),
    # processor=Processor(),
    num_workers=4,
)

async def main():
    while True:
        await asyncio.to_thread(input, "🔵")
        # agent.run(Message(
        #     id='abc123',
        #     content={'input': 'tubarao branco!'},
        #     history=[],
        #     role='user',
        #     source=None
        # ))
        agent.inputs_queue.put(Message(
            id='abc123',
            content={'input': 'tubarao branco!'},
            history=[],
            role='user',
            source=None
        ))
        print(await agent._start())

        # if 'abc123' not in agent.llm.metadata:
        #     print('🟢 Nenhuma chamada para o LLM')
        #     continue
        # for cost in agent.llm.metadata['abc123']:
        #     print(cost)

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()



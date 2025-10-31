import asyncio
import random
import uuid
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from src.message import Message
from agents.nectar.input_classifier import input_classifier_fn
from agents.nectar.direct_response import direct_response_fn
from agents.nectar.blog.blog_query_rag import blog_query_rag_fn
from agents.nectar.out_of_scope_response import out_of_scope_response_fn
from agents.nectar.blog.blog_response import blog_response_fn
from agents.nectar.telegram_sender import telegram_sender_fn

load_dotenv()

app = FastAPI()

input_classifier = input_classifier_fn('input_classifier')
direct_response = direct_response_fn('direct_response')
blog_query_rag = blog_query_rag_fn('blog_query_rag')
out_of_scope_response = out_of_scope_response_fn('out_of_scope')
blog_response = blog_response_fn('blog_response')
telegram_sender = telegram_sender_fn('telegram_sender')

input_classifier.connect(direct_response)
input_classifier.connect(out_of_scope_response)
input_classifier.connect(blog_query_rag)

blog_query_rag.connect(blog_response)

direct_response.connect(telegram_sender, required=False)
out_of_scope_response.connect(telegram_sender, required=False)
blog_response.connect(telegram_sender, required=False)

# blog_query_rag.plot()

random_messages = [
    'olá, tudo bem?',
    'O que é um CRM?',
    'me fale como implementar uma pipeline de vendas',
    'como montar uma estratégia de vendas?',
    'explique como usar a API para pegar os metadados de uma venda',
    'fale uma estratégia de ganhar dinheiro com o mercado financeiro',
]

class InputMessage(BaseModel):
    chat_id: str
    message: str

    class Config:
        json_schema_extra = {
            "examples": [{
                "chat_id": str(uuid.uuid4()),
                "message": random.choice(random_messages)
            }]
        }

@app.post("/send_message")
async def send_message(input_message: InputMessage):
    input_classifier.run(Message(
        id=input_message.chat_id,
        content={'input': input_message.message},
        history=[
            Message(
                id=input_message.chat_id,
                content={'input': 'faça uma pergunta sobre o CRM'},
                history=[],
                role='assistant',
                source=None
            )
        ],
        role='user',
        source=None
    ))
    return {"status": "received"}

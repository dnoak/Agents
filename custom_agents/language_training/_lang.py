import asyncio
import os
import random
from src.message import Message, Messages
from src.agent import Agent
from agents.language_training.topic_classifier import topic_classifier_fn
from agents.language_training.topic_generator import topic_generator_fn
from agents.language_training.user_input import user_input_fn
from agents.language_training.topic_choice import topic_choice_fn


topic_choice = topic_choice_fn('topic_choice')
topic_generator = topic_generator_fn('topic_generator')
user_input = user_input_fn('user_input')
topic_classifier = topic_classifier_fn('topic_classifier')


topic_choice.connect(topic_generator)
topic_generator.connect(user_input)
user_input.connect(topic_classifier)
topic_classifier.connect(topic_choice, required=False)

topic_classifier.plot()

async def send_inputs():
    #while True:
        # user_input = await asyncio.to_thread(input, "Input: ")
    topic_choice.run(Messages(
        id='id_123',
        data=[Message(content={"topic": "...", "user_input": "..."}, role='user')],
        source=None
    ))
    while True:
        await asyncio.sleep(5)

if __name__ == '__main__':
    os.system('cls')

    loop = asyncio.get_event_loop()
    loop.create_task(send_inputs())
    loop.run_forever()

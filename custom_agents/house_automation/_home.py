import asyncio
from agents.house_automation.input_classifier import home_automation_classifier_fn
from agents.house_automation.lights_control import light_control_fn
from agents.house_automation.climate_info import climate_info_fn
from src.message import Message
import logging
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)


classifier = home_automation_classifier_fn('home_automation_classifier', debug=True)
light_control = light_control_fn('light_control', debug=True)
climate_info = climate_info_fn('climate_info', debug=True)

classifier.connect(light_control)
classifier.connect(climate_info, required=False)
climate_info.connect(climate_info, required=False)

# classifier.plot()

async def send_inputs():
    while True:
        user_input = await asyncio.to_thread(input, "Input: ")
        classifier.run(Message(
            id='id_123',
            content={'user_input': user_input}, 
            history=[],
            role='user',
            source=None
        ))


loop = asyncio.get_event_loop()
loop.create_task(send_inputs())
loop.run_forever()


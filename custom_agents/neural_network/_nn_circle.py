import asyncio
import random
import threading
import time
from src.message import Message, Messages
from custom_agents.neural_network.neuron import neuron_fn

x, y, z = 2.8, 0.5, 0

input_x = neuron_fn('x', [1], 0)
input_y = neuron_fn('y', [1], 0)
input_z = neuron_fn('z', [1], 0)

neuron_0 = neuron_fn('agent_neuron_0', [-0.69, -0.77, 0], -0.23)
neuron_1 = neuron_fn('agent_neuron_1', [-0.26, +0.97, 0], -0.29)
neuron_2 = neuron_fn('agent_neuron_2', [+0.95, -0.19, 0], -0.27)

neuron_3 = neuron_fn('agent_neuron_3', [0.93, 0.99, 0.93], -1.4)

neuron_4 = neuron_fn('agent_neuron_4', [-1], 1)


# l0
input_x.connect(neuron_0)
input_x.connect(neuron_1)
input_x.connect(neuron_2)

input_y.connect(neuron_0)
input_y.connect(neuron_1)
input_y.connect(neuron_2)

input_z.connect(neuron_0)
input_z.connect(neuron_1)   
input_z.connect(neuron_2)

# l1
neuron_0.connect(neuron_3)
neuron_1.connect(neuron_3)
neuron_2.connect(neuron_3)

# # l2
neuron_3.connect(neuron_4)

# neuron_4.connect(input_x)
# neuron_4.connect(input_y)
# neuron_4.connect(input_z)


input_x.plot()

async def send_inputs():
    while True:
        await asyncio.to_thread(input, "Pressione Enter para enviar inputs...")
        id_xyz = str(random.randint(0, 10000))
        print(f"🟡 enviando {id_xyz}")
        # input_z.run(Messages(
        #     id=id_xyz,
        #     content={'a': z},
        #     history=[],
        #     role='user',
        #     source=None
        # ))
        input_y.run(Messages(
            id=id_xyz,
            data=[Message(content={'a': y}, role='user')],
            source=None
        ))
        input_z.run(Messages(
            id=id_xyz,
            data=[Message(content={'a': z}, role='user')],
            source=None
        ))
        input_x.run(Messages(
            id=id_xyz,
            data=[Message(content={'a': x}, role='user')],
            source=None
        ))

loop = asyncio.get_event_loop()
loop.create_task(send_inputs())
loop.run_forever()


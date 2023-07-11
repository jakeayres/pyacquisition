from src.instruments import Gizmotron, WaveformGenerator, Clock
from src import Broadcaster, Consumer, Graph, Scribe, Rack, Experiment

import asyncio, json


async def sweep_gizmotron(
	#graph: Graph,
	scribe: Scribe, 
	gizmo: Gizmotron, 
	max_value: float,
	pause: float = 1,
	):

	await asyncio.sleep(pause)

	scribe.next_file('Up Positive', new_chapter=True)
	await asyncio.sleep(pause)

	gizmo.set_setpoint(max_value)
	while gizmo.get_value() < max_value:
		await asyncio.sleep(0.25)

	await asyncio.sleep(pause)
	scribe.next_file('Down Positive')
	await asyncio.sleep(pause)

	gizmo.set_setpoint(0)
	while gizmo.get_value() > 0:
		await asyncio.sleep(0.25)

	await asyncio.sleep(pause)
	scribe.next_file('Up Negative')
	await asyncio.sleep(pause)

	gizmo.set_setpoint(-max_value)
	while gizmo.get_value() > -max_value:
		await asyncio.sleep(0.25)

	await asyncio.sleep(pause)
	scribe.next_file('Down Negative')
	await asyncio.sleep(1)

	gizmo.set_setpoint(0)
	while gizmo.get_value() < 0:
		await asyncio.sleep(0.25)

	# graph.save(f'Sweep{max_value}.png')
	# graph.clear()







class MyExperiment(Experiment):


	async def execute(self):

		#graph = self.add_async_graph('time', 'value')

		#g2 = self.add_async_graph('value', 'signal_1')

		await sweep_gizmotron(self.scribe, self.rack.gizmo, 3)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 4)





e = MyExperiment(
	root='./data/',
	rack_config='./soft_config.json',
)

asyncio.run(e.run())

"""
Maybe the Experiment class should take instruments or the rack
as an argument. Something like:

rack = Rack.from_file('config.json')
e = Experiment('./data/', rack)

or

e = Experiment('./data/', lockins=[Lockin1, Lockin2])


Experiments take instruments as arguements and can then update
things like the rack measurements accordingly eg lockin.get_x
and get_y can be added for each Lockin.

"""
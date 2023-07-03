import asyncio
import datetime






class SequentialTask:

	def __init__(self, name, tasks=None):
		self.name = name
		self.tasks = tasks or []


	async def run(self):
		print(f'{datetime.datetime.now()} :: Running Task :: {self.name}')
		for task in self.tasks:
			await task.run()


class ConcurrentTask:

	def __init__(self, name, tasks=None):
		self.name = name
		self.tasks = tasks or []


	async def run(self):
		print(f'{datetime.datetime.now()} :: Running Task :: {self.name}')
		await asyncio.gather(*[task.run() for task in self.tasks])



class Task:


	def __init__(self, name, func):
		self.name = name
		self.func = func


	async def run(self):
		print(f'{datetime.datetime.now()} :: Running Task :: {self.name} :: {self.func()}')
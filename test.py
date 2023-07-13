import asyncio
import websockets
import random
import json
import datetime

from src.experiment import Experiment

from src.instruments import Clock, WaveformGenerator, Gizmotron, SR_830

from src.coroutines import pause, sweep_gizmotron

from fastapi import FastAPI, WebSocket
import uvicorn

from src.visa import resource_manager

import serial




lockin = SR_830(
	uid='lockin', 
	visa_resource=resource_manager(backend='prologix', com_port=3).open_resource('GPIB0::12::INSTR'),
)


for i in range(10):
	print('Setting:', datetime.datetime.now())
	lockin.set_frequency(i)
	print('Set    :', datetime.datetime.now())

	print('Getting:', datetime.datetime.now())
	print(lockin.get_frequency())
	print('Got    :', datetime.datetime.now())


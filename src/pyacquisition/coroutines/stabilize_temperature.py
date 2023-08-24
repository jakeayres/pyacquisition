from ..instruments import Lakeshore_340, Lakeshore_350
from ..instruments.lakeshore.lakeshore_340 import InputChannel as IC340
from ..instruments.lakeshore.lakeshore_350 import InputChannel as IC350
from ..scribe import Scribe
from ._coroutine import Coroutine


import asyncio
from dataclasses import dataclass



@dataclass
class StabilizeTemperature(Coroutine):

	scribe: Scribe
	lakeshore: Lakeshore_340 | LakeShore_350
	temperature: float,
	ramp_rate: float,
	tolerance: float = 10e-3,
	input_channel: IC340 | IC350,
	from_cache: bool = False

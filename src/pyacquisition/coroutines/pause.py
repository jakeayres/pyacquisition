from ..scribe import Scribe

import asyncio


async def pause(
	scribe: Scribe, 
	period=1
	):
	scribe.log(f'Pausing for {period} s')
	await asyncio.sleep(period)
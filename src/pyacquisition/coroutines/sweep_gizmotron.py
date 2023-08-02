from ..instruments import Gizmotron
from ..scribe import Scribe


import asyncio
from dataclasses import dataclass



async def sweep_gizmotron(
    scribe: Scribe, 
    gizmo: Gizmotron, 
    max_value: float,
    pause: float = 1,
    from_cache: bool = False,
    ):
    """
    { function_description }

    :param      scribe:      The scribe
    :type       scribe:      Scribe
    :param      gizmo:       The gizmo
    :type       gizmo:       Gizmotron
    :param      max_value:   The maximum value
    :type       max_value:   float
    :param      pause:       The pause
    :type       pause:       float
    :param      from_cache:  The from cache
    :type       from_cache:  bool
    """


    await asyncio.sleep(pause)

    scribe.next_file('Up Positive', new_chapter=True)
    await asyncio.sleep(pause)

    gizmo.set_setpoint(max_value)
    while gizmo.get_value(from_cache=from_cache) < max_value:
        await asyncio.sleep(pause)

    await asyncio.sleep(pause)
    scribe.next_file('Down Positive')
    await asyncio.sleep(pause)

    gizmo.set_setpoint(0)
    while gizmo.get_value(from_cache=from_cache) > 0:
        await asyncio.sleep(pause)

    await asyncio.sleep(pause)
    scribe.next_file('Up Negative')
    await asyncio.sleep(pause)

    gizmo.set_setpoint(-max_value)
    while gizmo.get_value(from_cache=from_cache) > -max_value:
        await asyncio.sleep(pause)

    await asyncio.sleep(pause)
    scribe.next_file('Down Negative')
    await asyncio.sleep(pause)

    gizmo.set_setpoint(0)
    while gizmo.get_value(from_cache=from_cache) < 0:
        await asyncio.sleep(pause)

    scribe.next_file('Sweep Finished')



@dataclass
class SweepGizmotron:

    scribe: Scribe
    gizmo: Gizmotron
    max_value: float
    pause: float = 1
    from_cache: bool = False


    def string(self):
        return f'SweepGizmotron up to {self.max_value}'


    async def coroutine(self):

        await asyncio.sleep(self.pause)

        self.scribe.next_file('Up Positive', new_chapter=True)
        await asyncio.sleep(self.pause)

        self.gizmo.set_setpoint(self.max_value)
        while self.gizmo.get_value(from_cache=self.from_cache) < self.max_value:
            await asyncio.sleep(self.pause)

        await asyncio.sleep(self.pause)
        self.scribe.next_file('Down Positive')
        await asyncio.sleep(self.pause)

        self.gizmo.set_setpoint(0)
        while self.gizmo.get_value(from_cache=self.from_cache) > 0:
            await asyncio.sleep(self.pause)

        await asyncio.sleep(self.pause)
        self.scribe.next_file('Up Negative')
        await asyncio.sleep(self.pause)

        self.gizmo.set_setpoint(-self.max_value)
        while self.gizmo.get_value(from_cache=self.from_cache) > -self.max_value:
            await asyncio.sleep(self.pause)

        await asyncio.sleep(self.pause)
        self.scribe.next_file('Down Negative')
        await asyncio.sleep(self.pause)

        self.gizmo.set_setpoint(0)
        while self.gizmo.get_value(from_cache=self.from_cache) < 0:
            await asyncio.sleep(self.pause)

        self.scribe.next_file('Sweep Finished')





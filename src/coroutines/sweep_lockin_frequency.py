from ..instruments import SR_830
from ..scribe import Scribe


import asyncio


async def sweep_lockin_frequency(
    scribe: Scribe, 
    lockin: SR_830,
    min_value: float,
    max_value: float,
    pause: float = 1,
    ):
    """
    { function_description }

    :param      scribe:     The scribe
    :type       scribe:     Scribe
    :param      gizmo:      The gizmo
    :type       gizmo:      Gizmotron
    :param      max_value:  The maximum value
    :type       max_value:  float
    :param      pause:      The pause
    :type       pause:      float
    """

    await asyncio.sleep(pause)

    frequency = min_value
    lockin.set_frequency(frequency)

    scribe.next_file('Sweep up', new_chapter=True)
    await asyncio.sleep(pause)
    while frequency < max_value:
        await asyncio.sleep(pause)
        frequency += 1
        lockin.set_frequency(frequency)

    scribe.next_file('Ended', new_chapter=False)


from ..instruments import Gizmotron
from ..scribe import Scribe


import asyncio



async def sweep_gizmotron(
    scribe: Scribe, 
    gizmo: Gizmotron, 
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



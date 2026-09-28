"""The rack's cycle (core/rack.py): measurements, then each trace source's
columns, in one row."""

import asyncio

import pytest

from pyacquisition.core.consumer import Consumer
from pyacquisition.core.measurement import Measurement
from pyacquisition.core.rack import Rack


class Source:
    """A trace source that takes a while, and notes what each row gave it."""

    def __init__(self, name, wait=0.0):
        self.name, self.wait, self.seen = name, wait, []

    async def row_columns(self, row):
        self.seen.append(dict(row))
        await asyncio.sleep(self.wait)
        return {f"{self.name}_index": len(self.seen) - 1}


@pytest.mark.asyncio
async def test_a_row_has_the_measurements_and_each_sources_columns():
    rack = Rack()
    rack.add_measurement(Measurement("x", lambda: 1.5))
    first, second = Source("a"), Source("b", wait=0.05)
    rack.trace_sources = [first, second]
    consumer = Consumer()
    rack.subscribe(consumer)

    await rack.measure()
    await rack.measure()

    rows = [consumer.queue.get_nowait() for _ in range(2)]
    assert rows == [{"x": 1.5, "a_index": 0, "b_index": 0}, {"x": 1.5, "a_index": 1, "b_index": 1}]
    # Each source is given the row's measurements only, not another's columns.
    assert first.seen == second.seen == [{"x": 1.5}, {"x": 1.5}]


@pytest.mark.asyncio
async def test_a_row_waits_for_its_sources():
    rack = Rack()
    rack.add_measurement(Measurement("x", lambda: 1.0))
    rack.trace_sources = [Source("slow", wait=0.2)]
    consumer = Consumer()
    rack.subscribe(consumer)

    measuring = asyncio.create_task(rack.measure())
    await asyncio.sleep(0.1)
    assert consumer.queue.empty()
    await measuring
    assert consumer.queue.get_nowait() == {"x": 1.0, "slow_index": 0}

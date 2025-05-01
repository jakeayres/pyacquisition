from ..core.task import Task
import asyncio

from .wait import WaitFor, WaitUntil


standard_tasks = [
    WaitFor,
    WaitUntil
]


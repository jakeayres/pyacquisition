"""An instrument's query or command, queued to run in its turn like any task.

`InstrumentCall` holds the instrument's id, the method's name and its inputs,
fixed when it is queued. Running it calls the method, as the instrument's own
endpoint does: a query's answer is logged and kept, so the task manager's last
result shows it, and a command is logged as sent.

`register_call_endpoints` gives each task manager an endpoint for each query and
command of each instrument, `<manager path>/call/<uid>/<method>`, with the same
inputs as the instrument's endpoint, and a maker for each, so that a saved
sequence holding a call loads it again.
"""

import inspect
from dataclasses import dataclass, field
from enum import Enum

from fastapi import HTTPException

from ..history import json_value
from ..instrument import resolve_enum_kwargs
from ..logging import logger
from .task import Task

KEY = "call:"  # before `<uid>.<method>`, the key of a call in a saved sequence


def _text(value):
    """An input as it is shown and saved: an enum by its member's name."""
    return value.name if isinstance(value, Enum) else value


@dataclass
class InstrumentCall(Task):
    """An instrument's query or command, queued.

    Attributes:
        instrument (str): The instrument's id.
        method (str): The query's or command's name.
        arguments (dict): Its inputs, by name. An enum is given by its member's
            name or label, or as the member.
    """

    instrument: str
    method: str
    arguments: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.instrument}.{self.method}"

    @property
    def description(self) -> str:
        inputs = ", ".join(f"{key}={_text(value)}" for key, value in self.arguments.items())
        return f"{self.name}({inputs})"

    @property
    def parameters(self) -> dict | None:
        return {key: _text(value) for key, value in self.arguments.items()} or None

    async def run(self, experiment=None):
        instrument = experiment.instruments.get(self.instrument)
        if instrument is None:
            raise RuntimeError(f"There is no instrument called '{self.instrument}'.")
        method = getattr(instrument, self.method)
        answer = method(**resolve_enum_kwargs(method, self.arguments))
        if inspect.isawaitable(answer):
            answer = await answer
        if getattr(method, "_is_query", False):
            # Kept for the task manager's last result (see TaskManager._finished).
            self._result = answer
            self.log(f"{self.description} → {json_value(answer)}")
        else:
            self.log(f"{self.description} sent")


def calls(instrument) -> dict:
    """An instrument's queries and commands, by name, as bound methods."""
    return {
        name: method
        for name, method in inspect.getmembers(instrument, predicate=inspect.ismethod)
        if getattr(method, "_is_query", False) or getattr(method, "_is_command", False)
    }


def register_call_endpoints(api_server, task_manager, uid: str, instrument) -> None:
    """Gives a task manager an endpoint that queues each of an instrument's
    queries and commands, and a maker for each, for saved sequences."""
    for method_name, method in calls(instrument).items():
        _register_one(api_server, task_manager, uid, method_name, method)


def _register_one(api_server, task_manager, uid, method_name, method) -> None:
    key = f"{KEY}{uid}.{method_name}"
    shown = f"{uid}.{method_name}"

    def make(kwargs: dict) -> InstrumentCall:
        """The call, from its inputs, recording how it was made (as an endpoint
        queues a task), so that it can be saved in a sequence and made again.
        Raises `ValueError` or `TypeError` if the inputs won't do."""
        unknown = sorted(set(kwargs) - set(inspect.signature(method).parameters))
        if unknown:
            raise TypeError(f"{shown} takes no input called {', '.join(unknown)}")
        resolve_enum_kwargs(method, kwargs)  # raises for a name no member has
        task = InstrumentCall(instrument=uid, method=method_name, arguments=dict(kwargs))
        task._queued_with = {
            "task": key,
            "name": shown,
            "parameters": {k: _text(v) for k, v in kwargs.items()},
        }
        return task

    task_manager._queueable[key] = make

    async def endpoint(**kwargs):
        try:
            task = make(kwargs)
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        task_manager.add_task(task)
        return {"status": 200, "message": f"{shown} queued"}

    endpoint.__name__ = f"queue_{uid}_{method_name}"
    endpoint.__doc__ = (
        f"Queues `{shown}` on this task manager, to run in its turn with these "
        f"inputs, as the instrument's own endpoint `/{uid}/{method_name}` calls it "
        "at once. A query's answer is logged, and is the task manager's last "
        f"result (`value`).\n\n{inspect.getdoc(method) or ''}"
    ).strip()
    endpoint.__signature__ = inspect.signature(method).replace(return_annotation=dict)
    endpoint.__annotations__ = {**method.__annotations__, "return": dict}
    api_server.app.add_api_route(
        f"{task_manager._path}/call/{uid}/{method_name}",
        endpoint,
        methods=["GET"],
        tags=[task_manager._api_tag],
    )
    logger.debug(f"{task_manager._tag} {shown} can be queued")

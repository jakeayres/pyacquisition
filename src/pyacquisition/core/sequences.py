"""Sequences: queues of tasks saved to use again, in this run or a later one.

A sequence is a JSON file in the `sequences` folder under the experiment's
`root_path`, named after it (`cooldown.json`). It lists each task as its
endpoint queued it: the endpoint's task (`"waitfor"`), the name shown, and the
inputs it was given. So it loads onto any task manager that can queue those
tasks, and a task that has since gained an input takes that input's default.

    {
      "name": "cooldown",
      "saved": "2026-09-27T10:12:00",
      "tasks": [
        {"task": "waitfor", "name": "WaitFor",
         "parameters": {"hours": 0, "minutes": 5, "seconds": 0}}
      ]
    }
"""

import datetime
import json
from pathlib import Path

from fastapi import HTTPException

from .logging import logger
from .scribe import title_problem

SUFFIX = ".json"


class SequenceError(ValueError):
    """A sequence can't be saved, found or loaded as asked."""


class Sequences:
    """The sequences saved in a folder, and the endpoints to use them."""

    def __init__(self, folder: Path, task_managers):
        """
        Args:
            folder (Path): Where the sequences are kept. Made when the first is
                saved.
            task_managers: The experiment's task managers, by name, which
                sequences are saved from and loaded onto.
        """
        self.folder = Path(folder)
        self._task_managers = task_managers

    # ------------------------------------------------------------ the files
    def _path(self, name: str) -> Path:
        problem = title_problem(name)
        if problem:
            raise SequenceError(problem.replace("title", "sequence's name"))
        return self.folder / f"{name.strip()}{SUFFIX}"

    def list(self) -> list[dict]:
        """Every sequence saved, by name: when it was saved, and its tasks'
        names. A file that can't be read is left out, and logged."""
        found = []
        if not self.folder.is_dir():
            return found
        for path in sorted(self.folder.glob(f"*{SUFFIX}"), key=lambda p: p.stem.lower()):
            try:
                sequence = self._read(path)
            except SequenceError as error:
                logger.warning(f"[Sequences] {error}")
                continue
            found.append(
                {
                    "name": path.stem,
                    "saved": sequence.get("saved"),
                    "tasks": [t.get("name") or t.get("task") for t in sequence["tasks"]],
                }
            )
        return found

    def _read(self, path: Path) -> dict:
        try:
            sequence = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SequenceError(f"Can't read the sequence {path.name}: {error}") from error
        tasks = sequence.get("tasks") if isinstance(sequence, dict) else None
        if not isinstance(tasks, list) or not all(
            isinstance(t, dict) and isinstance(t.get("task"), str) for t in tasks
        ):
            raise SequenceError(f"The sequence {path.name} has no list of tasks.")
        return sequence

    def read(self, name: str) -> dict:
        """The sequence saved under this name."""
        path = self._path(name)
        if not path.is_file():
            raise SequenceError(f"There is no sequence called {name!r}.")
        return self._read(path)

    def save(self, name: str, tasks: list, overwrite: bool = False) -> Path:
        """Saves tasks (as `TaskManager.saveable` gives them) as a sequence.

        Raises:
            FileExistsError: If there is one of that name already, and not
                `overwrite`.
            SequenceError: If the name can't be a file's.
        """
        path = self._path(name)
        if path.exists() and not overwrite:
            raise FileExistsError(f"There is already a sequence called {name!r}.")
        self.folder.mkdir(parents=True, exist_ok=True)
        sequence = {
            "name": name.strip(),
            "saved": datetime.datetime.now().isoformat(timespec="seconds"),
            "tasks": tasks,
        }
        path.write_text(json.dumps(sequence, indent=2), encoding="utf-8")
        logger.info(f"[Sequences] Saved {len(tasks)} tasks as '{path}'")
        return path

    def delete(self, name: str) -> None:
        path = self._path(name)
        if not path.is_file():
            raise SequenceError(f"There is no sequence called {name!r}.")
        path.unlink()
        logger.info(f"[Sequences] Deleted '{path}'")

    # ------------------------------------------------------------ the endpoints
    def _manager(self, name: str):
        manager = self._task_managers.get(name)
        if manager is None:
            raise HTTPException(status_code=422, detail=f"There is no task manager called {name!r}.")
        return manager

    def _register_endpoints(self, api_server):
        @api_server.app.get("/sequences", tags=["sequences"])
        async def list_sequences():
            """
            The sequences saved, each with its `name`, when it was `saved` and its
            `tasks`' names, in order.
            """
            return {"status": 200, "data": self.list()}

        @api_server.app.get("/sequences/save", tags=["sequences"])
        async def save_sequence(
            name: str,
            manager: str = "main",
            include_running: bool = True,
            overwrite: bool = False,
        ):
            """
            Save a task manager's queue as a sequence (starting with its running
            task, unless `include_running` is false). Tasks queued other than from
            the API, such as in `setup()`, can't be saved, and are listed as
            `skipped`. A sequence of the same name is replaced only with
            `overwrite`; otherwise it is a 409.
            """
            tasks, skipped = self._manager(manager).saveable(include_running)
            if not tasks:
                raise HTTPException(status_code=422, detail="There are no tasks to save.")
            try:
                self.save(name, tasks, overwrite=overwrite)
            except FileExistsError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except SequenceError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            return {"status": 200, "saved": len(tasks), "skipped": skipped}

        @api_server.app.get("/sequences/load", tags=["sequences"])
        async def load_sequence(name: str, manager: str = "main"):
            """
            Queue a sequence's tasks on a task manager, after those already
            queued. Nothing is queued unless every task can be: otherwise it is a
            422 listing what is wrong with each.
            """
            try:
                sequence = self.read(name)
                queued = self._manager(manager).queue_saved(sequence["tasks"])
            except ValueError as error:  # SequenceError included
                raise HTTPException(status_code=422, detail=str(error)) from error
            logger.info(f"[Sequences] Queued '{name}' ({queued} tasks) on {manager}")
            return {"status": 200, "queued": queued}

        @api_server.app.get("/sequences/delete", tags=["sequences"])
        async def delete_sequence(name: str):
            """Delete a saved sequence."""
            try:
                self.delete(name)
            except SequenceError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            return {"status": 200, "message": f"Deleted {name}."}

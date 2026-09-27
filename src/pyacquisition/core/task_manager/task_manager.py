from ..history import json_value
from ..logging import logger
from .task import Task
import asyncio
import dataclasses
import time
import math
from fastapi import HTTPException
from typing import Literal


def _json_safe(value):
    """A value that can be sent as JSON: `nan` and objects become text."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    return str(value)


class TaskManager:
    """
    TaskManager is a class that manages a queue of tasks. It is used by the
    Experiment class to manage the user-defined tasks.

    An experiment can have several task managers, each with its own queue. They
    run at the same time, and each runs its own tasks one after another.
    """

    def __init__(
        self,
        name: str = "main",
        path: str = "/task_manager",
        tasks_path: str = "/tasks",
    ):
        """
        Args:
            name (str): The name of this task manager.
            path (str): Where the API endpoints that control this task manager
                (pause, resume, abort and so on) are placed.
            tasks_path (str): Where the endpoints that queue the registered tasks
                are placed.
        """
        self.name = name
        self._path = path.rstrip("/")
        self._tasks_path = tasks_path.rstrip("/")
        self._tag = "[TaskManager]" if name == "main" else f"[TaskManager:{name}]"
        self._api_tag = "Task Manager" if name == "main" else f"Task Manager: {name}"

        self._current_task: Task = None
        self._last_result: dict | None = None
        self._task_queue = asyncio.Queue()
        self._pause_event = asyncio.Event()
        self._pause_event.set()

        self._task_registry = {}
        # How each task that can be queued here is made, by its endpoint's name
        # ("waitfor"), from the inputs it is given (see Task.register_endpoints).
        self._queueable = {}
        self._shutdown_event = asyncio.Event()
        self._display_errors = set()

    async def setup(self):
        """
        Setup the task manager.
        """
        logger.debug(f"{self._tag} Setup started")
        logger.debug(f"{self._tag} Setup completed")

    async def run(self, experiment) -> None:
        """
        The main loop that runs the tasks in the queue.
        """
        logger.info(f"{self._tag} Waiting for task to appear on queue")
        while True:
            await self._pause_event.wait()

            if self._shutdown_event.is_set():
                break  # do not start queued tasks while shutting down

            try:
                self._current_task = await asyncio.wait_for(
                    self._task_queue.get(), timeout=0.1
                )
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error(f"{self._tag} Error getting task from queue: {e}")

            if self._current_task and not self._pause_event.is_set():
                # Paused while waiting for a task: it goes back to the front of
                # the queue, to start when the task manager is resumed.
                self._task_queue._queue.appendleft(self._current_task)
                self._current_task = None
                continue

            if self._current_task:
                task = self._current_task
                logger.info(f"{self._tag} Task fetched from queue: {task.name}")
                try:
                    await task.start(experiment=experiment)
                except Exception as e:
                    logger.error(f"Error running task {task}: {e}")
                finally:
                    self._current_task = None
                    self._finished(task)
                    logger.info(f"{self._tag} Waiting for task to appear on queue")

            if self._shutdown_event.is_set():
                break

    def _finished(self, task: Task) -> None:
        """
        Notes how a task ended. A task that failed pauses the queue, like an abort
        does, so that the tasks behind it, which may rely on it having worked, do
        not run on their own. Resume the task manager to carry on with them.
        """
        outcome = task.outcome or "failed"
        error = task.failure
        self._last_result = {
            "name": task.name,
            "outcome": outcome,
            "error": None if error is None else f"{type(error).__name__}: {error}",
            # When it ended, which also tells two results alike apart (the
            # interface raises an alert for each failure).
            "finished_at": time.time(),
            # What it read, if it is an instrument's queued query (InstrumentCall).
            "value": json_value(getattr(task, "_result", None)),
        }
        if outcome == "failed" and not self._shutdown_event.is_set():
            logger.error(
                f"{self._tag} {task.name} failed, so the task manager is paused. "
                "Resume it to carry on with the queue."
            )
            self.pause()

    async def teardown(self):
        """
        Teardown the task manager.
        """
        logger.debug(f"{self._tag} Teardown started")
        logger.debug(f"{self._tag} Teardown completed")

    async def shutdown(self):
        """
        Shutdown the task manager.
        """
        logger.debug(f"{self._tag} Shutdown started")
        self._shutdown_event.set()

        self.abort()

        # A paused task manager (after Pause, or after an Abort) waits for a resume
        # and would never see the shutdown event.
        self._pause_event.set()

    def pause(self):
        """
        Pause the task manager.
        """
        self._pause_event.clear()
        if self._current_task:
            self._current_task.pause()
        logger.info(f"{self._tag} paused.")

    def resume(self):
        """
        Resume the task manager.
        """
        self._pause_event.set()
        if self._current_task:
            self._current_task.resume()
        logger.info(f"{self._tag} Resumed.")

    def abort(self):
        """
        Abort the current task.
        """
        if self._current_task:
            self._current_task.abort()
            logger.info(f"{self._tag} Task manager aborted current task.")
            self.pause()
        else:
            logger.info(f"{self._tag} No task to abort.")

    def current_task(self) -> Task:
        """
        Get the current task.
        """
        return self._current_task

    def _display(self, task: Task) -> dict:
        """
        A task's id, name, description and parameters, safe to send to the interface.

        A description or parameter that raises an error, or that cannot be sent as
        JSON, must not stop the interface from seeing every other task, so the
        problem is logged once and the task is shown by its name alone.
        """
        try:
            display = task.display_dict()
            parameters = display["parameters"]
            return {
                "id": task._id,
                "name": display["name"],
                "description": _json_safe(display["description"]),
                "parameters": None
                if parameters is None
                else {str(k): _json_safe(v) for k, v in parameters.items()},
            }
        except Exception as e:
            problem = (type(task).__name__, str(e))
            if problem not in self._display_errors:
                self._display_errors.add(problem)
                logger.warning(f"{self._tag} Cannot show {problem[0]} in full: {e}")
            return {
                "id": task._id,
                "name": task.name,
                "description": None,
                "parameters": None,
            }

    def _timing(self, task: Task) -> dict:
        """
        When the running task started, how long it has run (not counting pauses),
        and how far along it is (see `Task.set_progress`), with its running
        subtasks' progress. A task that can't say is shown without it.
        """
        def safe(progress):
            if progress is None:
                return None
            return {key: _json_safe(value) for key, value in progress.items()}

        try:
            timing = task.timing()
            timing["progress"] = safe(timing["progress"])
            for subtask in timing["subtasks"]:
                subtask["name"] = _json_safe(subtask["name"])
                subtask["progress"] = safe(subtask["progress"])
            return timing
        except Exception as e:  # noqa: BLE001 - the rest of the state still shows
            logger.debug(f"{self._tag} Cannot show how far along {task.name} is: {e}")
            return {"started_at": None, "elapsed": None, "progress": None, "subtasks": []}

    def state(self) -> dict:
        """
        A snapshot of this task manager for the interface: whether it is running or
        paused, the task that is running, and the tasks waiting in the queue. The
        running task and each queued task are given as a name, a description and the
        parameters to show, with the id that picks the task out (see
        `remove_queued_task`). The running task also has `started_at`, `elapsed`,
        `progress` and `subtasks` (see `Task.timing`).

        `aborting` is true from the moment the running task is told to stop until it
        has finished, which is at its next step.
        """
        task = self._current_task
        return {
            "status": "Running" if self._pause_event.is_set() else "Paused",
            "current_task": {**self._display(task), **self._timing(task)} if task else None,
            "aborting": bool(task and task._abort_event.is_set()),
            "last_result": self._last_result,
            "queue": [self._display(queued) for queued in self._task_queue._queue],
        }

    def add_task(self, task: Task):
        """
        Add a task to the queue.
        """
        logger.info(f"{self._tag} Adding task to queue: {task.name}")
        self._task_queue.put_nowait(task)

    async def remove_task(self, index: int):
        """
        Remove a task from the queue.
        """
        if index < 0:
            index = len(self._task_queue._queue) + index

        if (index < len(self._task_queue._queue)) and (index >= 0):
            new_queue = asyncio.Queue()
            count = 0
            while not self._task_queue.empty():
                item = await self._task_queue.get()
                if count != index:
                    await new_queue.put(item)
                count += 1
            self._task_queue = new_queue
            logger.info(f"{self._tag} Removed task-{index} from queue")
        else:
            logger.warning(f"{self._tag} Index out of range: {index}")

    def remove_queued_task(self, task_id: str) -> bool:
        """
        Remove a task from the queue, given its id.

        Unlike `remove_task`, this cannot remove the wrong task if the queue has
        moved on since it was looked at, for example because the task in front of it
        has started. A task that is running is not in the queue, so it is not
        touched.

        Args:
            task_id (str): The id of the task, as given in `state()`.

        Returns:
            bool: Whether it was in the queue. It is not if it has already started,
                or been removed.
        """
        queue = self._task_queue._queue
        # Compare ids, not the tasks: equal tasks are different tasks.
        remaining = [task for task in queue if task._id != task_id]
        if len(remaining) == len(queue):
            logger.info(f"{self._tag} Task {task_id} is no longer in the queue")
            return False

        queue.clear()
        queue.extend(remaining)
        logger.info(f"{self._tag} Removed a task from the queue")
        return True

    def move_queued_task(self, task_id: str, direction: Literal["up", "down"]) -> bool:
        """
        Move a task one place along the queue, given its id.

        `up` is towards the front, so that it runs sooner, and `down` is towards the
        back. A task cannot be moved past either end. In particular the first task
        cannot go up: the place in front of it is the running task's, and the running
        task is not in the queue.

        Like `remove_queued_task`, it picks the task by its id, so it moves the right
        one even if the queue has moved on since it was looked at.

        Args:
            task_id (str): The id of the task, as given in `state()`.
            direction (str): `up` or `down`.

        Returns:
            bool: Whether it was moved. It is not if it is already at that end, or is
                no longer in the queue because it has started or been removed.

        Raises:
            ValueError: If the direction is not `up` or `down`.
        """
        if direction not in ("up", "down"):
            raise ValueError(f"direction must be 'up' or 'down', not {direction!r}.")

        queue = self._task_queue._queue
        tasks = list(queue)
        # Compare ids, not the tasks: equal tasks are different tasks.
        index = next((i for i, task in enumerate(tasks) if task._id == task_id), None)
        if index is None:
            logger.info(f"{self._tag} Task {task_id} is no longer in the queue")
            return False

        target = index - 1 if direction == "up" else index + 1
        if not 0 <= target < len(tasks):
            return False  # already at that end of the queue

        tasks[index], tasks[target] = tasks[target], tasks[index]
        queue.clear()
        queue.extend(tasks)
        logger.info(f"{self._tag} Moved a task {direction} the queue")
        return True

    def place_queued_task(self, task_id: str, index: int) -> bool:
        """
        Move a task to a place in the queue, given its id: 0 is the front, where it
        runs next. An index past either end puts it at that end.

        Like `move_queued_task`, it picks the task by its id, so it moves the right
        one even if the queue has moved on since it was looked at.

        Args:
            task_id (str): The id of the task, as given in `state()`.
            index (int): Where it goes, counting from 0 at the front.

        Returns:
            bool: Whether it moved. It does not if it is there already, or is no
                longer in the queue because it has started or been removed.
        """
        queue = self._task_queue._queue
        tasks = list(queue)
        current = next((i for i, task in enumerate(tasks) if task._id == task_id), None)
        if current is None:
            logger.info(f"{self._tag} Task {task_id} is no longer in the queue")
            return False
        index = max(0, min(index, len(tasks) - 1))
        if index == current:
            return False
        tasks.insert(index, tasks.pop(current))
        queue.clear()
        queue.extend(tasks)
        logger.info(f"{self._tag} Moved a task to place {index + 1} in the queue")
        return True

    def duplicate_queued_task(self, task_id: str) -> str | None:
        """
        Queue a copy of a task, with the same inputs, straight after it. The copy
        of the running task goes at the front of the queue, so it runs again next.

        Args:
            task_id (str): The id of the task, as given in `state()`.

        Returns:
            str | None: The copy's id, or None if the task is neither running nor
                in the queue any more.

        Raises:
            TypeError: If the task can't be copied (it is not a dataclass, or has
                inputs that aren't set when it is made).
        """
        queue = self._task_queue._queue
        tasks = list(queue)
        if self._current_task is not None and self._current_task._id == task_id:
            original, index = self._current_task, 0
        else:
            found = next((i for i, task in enumerate(tasks) if task._id == task_id), None)
            if found is None:
                logger.info(f"{self._tag} Task {task_id} is no longer in the queue")
                return None
            original, index = tasks[found], found + 1
        # A new task made from the same inputs, with an id and state of its own,
        # queued the same way.
        copy = dataclasses.replace(original)
        copy._queued_with = getattr(original, "_queued_with", None)
        tasks.insert(index, copy)
        queue.clear()
        queue.extend(tasks)
        logger.info(f"{self._tag} Duplicated {original.name} in the queue")
        return copy._id

    def saveable(self, include_running: bool = True) -> tuple[list, list]:
        """
        The tasks as they can be saved in a sequence: how each was queued (its
        endpoint's task and the inputs it was given), in order, starting with the
        running one if asked.

        Returns:
            tuple: The entries, and the names of the tasks that can't be saved
                because they weren't queued from the API (such as those queued in
                `setup()`).
        """
        tasks = list(self._task_queue._queue)
        if include_running and self._current_task is not None:
            tasks.insert(0, self._current_task)
        entries, skipped = [], []
        for task in tasks:
            record = getattr(task, "_queued_with", None)
            if record is None:
                skipped.append(task.name)
            else:
                entries.append(
                    {
                        "task": record["task"],
                        "name": record["name"],
                        "parameters": dict(record["parameters"]),
                    }
                )
        return entries, skipped

    def queue_saved(self, entries: list) -> int:
        """
        Queues the tasks of a saved sequence, after the tasks already queued. Each
        is made as its endpoint makes it, so an input it has since gained takes its
        default.

        Nothing is queued unless every task can be made.

        Args:
            entries (list): As `saveable` gives them.

        Returns:
            int: How many were queued.

        Raises:
            ValueError: If any can't be made here, listing each problem.
        """
        tasks, problems = [], []
        for number, entry in enumerate(entries, start=1):
            key = entry.get("task")
            shown = entry.get("name") or key
            make = self._queueable.get(key)
            if make is None:
                problems.append(f"{number}. {shown}: can't be queued here")
                continue
            try:
                tasks.append(make(dict(entry.get("parameters") or {})))
            except (TypeError, ValueError) as error:
                problems.append(f"{number}. {shown}: {error}")
        if problems:
            raise ValueError("\n".join(problems))
        for task in tasks:
            self.add_task(task)
        return len(tasks)

    async def clear_tasks(self):
        """
        Clear all tasks from the queue.
        """
        while not self._task_queue.empty():
            await self._task_queue.get()
        logger.info(f"{self._tag} All tasks cleared from queue")

    def register_task(self, experiment, task: Task, **kwargs) -> None:
        """
        Registers a task with the experiment, so that it can be queued on this
        task manager from the API.

        Args:
            task (Task): The task to register.
        """
        try:
            task.register_endpoints(
                experiment, task_manager=self, tasks_path=self._tasks_path, **kwargs
            )
            self._task_registry[task.__class__.__name__] = task
            # A task is registered as a class, and `name` is a property of its instances.
            name = task.__name__ if isinstance(task, type) else task.name
            logger.debug(f"Task '{name}' registered with the experiment")
        except Exception as e:
            logger.error(f"Error registering task {task.__class__.__name__}: {e}")
            raise

    def _register_endpoints(self, api_server):
        """
        Register the task manager endpoints with the API server.
        """

        @api_server.app.get(f"{self._path}/pause", tags=[self._api_tag])
        async def pause():
            """
            Endpoint to pause the task manager.
            """
            if not self._pause_event.is_set():
                return {
                    "status": "success",
                    "message": "Task manager is already paused.",
                }
            self.pause()
            return {"status": "success", "message": "Task manager paused."}

        @api_server.app.get(f"{self._path}/resume", tags=[self._api_tag])
        async def resume():
            """
            Endpoint to resume the task manager.
            """
            if self._pause_event.is_set():
                return {
                    "status": "success",
                    "message": "Task manager is already running.",
                }
            self.resume()
            return {"status": "success", "message": "Task manager resumed."}

        @api_server.app.get(f"{self._path}/abort", tags=[self._api_tag])
        async def abort_current_task():
            """
            Endpoint to abort the current task.
            """
            if not self._current_task:
                return {"status": "success", "message": "No task to abort."}
            self.abort()
            return {
                "status": "success",
                "message": "Task manager aborted current task.",
            }

        @api_server.app.get(f"{self._path}/remove_task", tags=[self._api_tag])
        async def remove_task(N: int) -> dict:
            """
            Remove the nth task from the queue
            """
            await self.remove_task(N)
            return {
                "status": "success",
                "message": f"Attempted to remove task-{N} from queue.",
            }

        @api_server.app.get(
            f"{self._path}/remove_queued_task",
            tags=[self._api_tag],
            include_in_schema=False,
        )
        async def remove_queued_task(task_id: str) -> dict:
            """
            Remove the task with this id from the queue. Its id is in the queue in
            `/managers/state`.
            """
            removed = self.remove_queued_task(task_id)
            return {
                "status": "success",
                "removed": removed,
                "message": "Task removed from queue."
                if removed
                else "That task is no longer in the queue.",
            }

        @api_server.app.get(
            f"{self._path}/move_queued_task",
            tags=[self._api_tag],
            include_in_schema=False,
        )
        async def move_queued_task(
            task_id: str, direction: Literal["up", "down"]
        ) -> dict:
            """
            Move the task with this id one place up (sooner) or down (later) the
            queue. Its id is in the queue in `/managers/state`.
            """
            moved = self.move_queued_task(task_id, direction)
            return {
                "status": "success",
                "moved": moved,
                "message": f"Task moved {direction}."
                if moved
                else "That task could not be moved.",
            }

        @api_server.app.get(
            f"{self._path}/place_queued_task",
            tags=[self._api_tag],
            include_in_schema=False,
        )
        async def place_queued_task(task_id: str, index: int) -> dict:
            """
            Move the task with this id to a place in the queue, 0 being the front.
            Its id is in the queue in `/managers/state`.
            """
            moved = self.place_queued_task(task_id, index)
            return {
                "status": "success",
                "moved": moved,
                "message": "Task moved." if moved else "That task was not moved.",
            }

        @api_server.app.get(
            f"{self._path}/duplicate_queued_task",
            tags=[self._api_tag],
            include_in_schema=False,
        )
        async def duplicate_queued_task(task_id: str) -> dict:
            """
            Queue a copy of the task with this id straight after it (or at the front,
            for the running task). Its id is in `/managers/state`.
            """
            try:
                copy = self.duplicate_queued_task(task_id)
            except (TypeError, ValueError) as error:
                raise HTTPException(
                    status_code=422, detail=f"That task can't be copied: {error}"
                ) from error
            return {
                "status": "success",
                "id": copy,
                "message": "Task duplicated."
                if copy
                else "That task is no longer in the queue.",
            }

        @api_server.app.get(f"{self._path}/clear_tasks", tags=[self._api_tag])
        async def clear_all_tasks():
            """
            Clear all queued tasks from the queue.
            """
            await self.clear_tasks()
            return {
                "status": "success",
                "message": "All tasks cleared from queue.",
            }

        @api_server.app.get(f"{self._path}/status", tags=[self._api_tag])
        async def status():
            """
            Endpoint to get the status of the task manager.
            """
            if self._pause_event.is_set():
                return {
                    "status": 200,
                    "data": "Running",
                }
            else:
                return {
                    "status": 200,
                    "data": "Paused",
                }

        @api_server.app.get(f"{self._path}/current_task", tags=[self._api_tag])
        async def current_task():
            """
            Endpoint to get the current task.
            """
            if self._current_task:
                return {
                    "status": 200,
                    "data": f"{self._current_task.name}",
                }
            else:
                return {
                    "status": 200,
                    "data": None,
                }

        @api_server.app.get(f"{self._path}/task_list", tags=[self._api_tag])
        async def task_list():
            """
            Endpoint to get the list of tasks in the queue.
            """
            tasks = []
            for task in self._task_queue._queue:
                tasks.append(task.display_dict())
            return {
                "status": 200,
                "data": tasks,
            }

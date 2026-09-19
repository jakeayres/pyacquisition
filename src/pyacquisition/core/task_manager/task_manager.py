from ..logging import logger
from .task import Task
import asyncio
import math
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
        self._task_queue = asyncio.Queue()
        self._pause_event = asyncio.Event()
        self._pause_event.set()

        self._task_registry = {}
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

            if self._current_task:
                logger.info(
                    f"{self._tag} Task fetched from queue: {self._current_task.name}"
                )
                try:
                    await self._current_task.start(experiment=experiment)
                except Exception as e:
                    logger.error(f"Error running task {self._current_task}: {e}")
                finally:
                    self._current_task = None
                    logger.info(f"{self._tag} Waiting for task to appear on queue")

            if self._shutdown_event.is_set():
                break

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

    def state(self) -> dict:
        """
        A snapshot of this task manager for the interface: whether it is running or
        paused, the task that is running, and the tasks waiting in the queue. The
        running task and each queued task are given as a name, a description and the
        parameters to show, with the id that picks the task out (see
        `remove_queued_task`).

        `aborting` is true from the moment the running task is told to stop until it
        has finished, which is at its next step.
        """
        task = self._current_task
        return {
            "status": "Running" if self._pause_event.is_set() else "Paused",
            "current_task": self._display(task) if task else None,
            "aborting": bool(task and task._abort_event.is_set()),
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
            logger.debug(f"Task '{task.name}' registered with the experiment")
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
        async def move_queued_task(task_id: str, direction: Literal["up", "down"]) -> dict:
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

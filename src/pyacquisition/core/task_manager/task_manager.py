from ..logging import logger
from .task import Task
import asyncio


class TaskManager:
    """
    TaskManager is a class that manages a queue of tasks. It is used by the
    Experiment class to manage the user-defined tasks."
    """

    def __init__(self):
        self._current_task: Task = None
        self._task_queue = asyncio.Queue()
        self._pause_event = asyncio.Event()
        self._pause_event.set()

        self._task_registry = {}
        self._shutdown_event = asyncio.Event()

    async def setup(self):
        """
        Setup the task manager.
        """
        logger.debug("[TaskManager] Setup started")
        logger.debug("[TaskManager] Setup completed")

    async def run(self, experiment) -> None:
        """
        The main loop that runs the tasks in the queue.
        """
        logger.info("[TaskManager] Waiting for task to appear on queue")
        while True:
            await self._pause_event.wait()

            try:
                self._current_task = await asyncio.wait_for(
                    self._task_queue.get(), timeout=0.1
                )
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error(f"[Taskmanager] Error getting task from queue: {e}")

            if self._current_task:
                logger.info(
                    f"[TaskManager] Task fetched from queue: {self._current_task.name}"
                )
                try:
                    await self._current_task.start(experiment=experiment)
                except Exception as e:
                    logger.error(f"Error running task {self._current_task}: {e}")
                finally:
                    self._current_task = None
                    logger.info("[TaskManager] Waiting for task to appear on queue")

            if self._shutdown_event.is_set():
                break

    async def teardown(self):
        """
        Teardown the task manager.
        """
        logger.debug("[TaskManager] Teardown started")
        logger.debug("[TaskManager] Teardown completed")

    async def shutdown(self):
        """
        Shutdown the task manager.
        """
        logger.debug("[TaskManager] Shutdown started")
        self._shutdown_event.set()

        self.abort()

    def pause(self):
        """
        Pause the task manager.
        """
        self._pause_event.clear()
        if self._current_task:
            self._current_task.pause()
        logger.info("[TaskManager] paused.")

    def resume(self):
        """
        Resume the task manager.
        """
        self._pause_event.set()
        if self._current_task:
            self._current_task.resume()
        logger.info("[TaskManager] Resumed.")

    def abort(self):
        """
        Abort the current task.
        """
        if self._current_task:
            self._current_task.abort()
            logger.info("[TaskManager] Task manager aborted current task.")
            self.pause()
        else:
            logger.info("[TaskManager] No task to abort.")

    def current_task(self) -> Task:
        """
        Get the current task.
        """
        return self._current_task

    def add_task(self, task: Task):
        """
        Add a task to the queue.
        """
        logger.info(f"[TaskManager] Adding task to queue: {task.name}")
        self._task_queue.put_nowait(task)

    def register_task(self, experiment, task: Task, **kwargs) -> None:
        """
        Registers a task with the experiment.

        Args:
            task (Task): The task to register.
        """
        try:
            task.register_endpoints(experiment, **kwargs)
            self._task_registry[task.__class__.__name__] = task
            logger.debug(f"Task '{task.name}' registered with the experiment")
        except Exception as e:
            logger.error(f"Error registering task {task.__class__.__name__}: {e}")
            raise

    def _register_endpoints(self, api_server):
        """
        Register the task manager endpoints with the API server.
        """

        @api_server.app.get("/task_manager/pause", tags=["Task Manager"])
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

        @api_server.app.get("/task_manager/resume", tags=["Task Manager"])
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

        @api_server.app.get("/task_manager/abort", tags=["Task Manager"])
        async def abort():
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

        @api_server.app.get("/task_manager/status", tags=["Task Manager"])
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

        @api_server.app.get("/task_manager/current_task", tags=["Task Manager"])
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

        @api_server.app.get("/task_manager/task_list", tags=["Task Manager"])
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

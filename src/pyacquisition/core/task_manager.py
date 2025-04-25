from .logging import logger
from .task import Task
import asyncio


class TaskManager:
    """
    TaskManager is a class that manages a queue of tasks. It is used by the
    Experiment class to manage the user-defined tasks."
    """

    def __init__(self):

        self.current_task: Task = None
        self._task_queue = asyncio.Queue()
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        
    
    def setup(self):
        """
        Setup the task manager.
        """
        logger.debug("Task manager setup started")
        logger.debug("Task manager setup completed")
        
        
    async def run(self):
        """
        The main loop that runs the tasks in the queue.
        """
        while True:
            try:
                await self._pause_event.wait()
                logger.debug("Waiting for task to appear on queue")
                self.current_task = await self._task_queue.get()
                logger.debug(f"Task fetched from queue: {self.current_task}")
                try:
                    await self.current_task.start()
                except Exception as e:
                    logger.error(f"Error running task {self.current_task}: {e}")
                finally:
                    self.current_task = None
            except Exception as e:
                logger.error(f"Error running task manager: {e}")




    def teardown(self):
        """
        Teardown the task manager.
        """
        logger.debug("Task manager teardown started")
        logger.debug("Task manager teardown completed")
        
        
    def pause(self):
        """
        Pause the task manager.
        """
        self._pause_event.clear()
        if self.current_task:
            self.current_task.pause()
        logger.info("Task manager paused.")
        
        
    def resume(self):
        """
        Resume the task manager.
        """
        self._pause_event.set()
        if self.current_task:
            self.current_task.resume()
        logger.info("Task manager resumed.")
        
        
    def add_task(self, task: Task):
        """
        Add a task to the queue.
        """
        logger.info(f"Adding task to queue: {task}")
        self._task_queue.put_nowait(task)
        
        
    def register_endpoints(self, api_server):
        """
        Register the task manager endpoints with the API server.
        """
        
        @api_server.app.get("/task_manager/pause")
        async def pause_endpoint():
            """
            Endpoint to pause the task manager.
            """
            if not self._pause_event.is_set():
                return {"status": "success", "message": "Task manager is already paused."}      
            self.pause()
            return {"status": "success", "message": "Task manager paused."}
        
        
        @api_server.app.get("/task_manager/resume")
        async def resume_endpoint():
            """
            Endpoint to resume the task manager.
            """
            if self._pause_event.is_set():
                return {"status": "success", "message": "Task manager is already running."}    
            self.resume()
            return {"status": "success", "message": "Task manager resumed."}
        
        
        @api_server.app.get("/task_manager/add_task")
        async def add_task_endpoint():
            """
            Endpoint to add a task to the queue.
            """
            from ..tasks import TestTask
            logger.info(f"Adding task to queue")
            self.add_task(TestTask())
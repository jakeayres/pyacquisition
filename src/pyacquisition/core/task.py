import asyncio
from ..core.logging import logger
from dataclasses import dataclass, field



@dataclass
class Task:
    """
    Base class for tasks in the experiment framework.
    
    Attributes:
        _pause_event (asyncio.Event): Event to control pausing of the task.
        _abort_event (asyncio.Event): Event to control aborting of the task.
        _is_paused (bool): Flag indicating if the task is paused.
        _status (str): Current status of the task.
    """
    
    _pause_event: asyncio.Event = field(init=False, default_factory=asyncio.Event)
    _abort_event: asyncio.Event = field(init=False, default_factory=asyncio.Event)
    _is_paused: bool = field(init=False, default=False)
    _status: str = field(init=False, default="running")
    
    
    def __post_init__(self):
        """
        Initialize the task with default events.
        """
        self._pause_event.set() # Set to allow task to run immediately
        self._abort_event.clear() # Clear to allow task to run immediately

        
    async def setup(self):
        """
        Override this method in subclasses to define setup tasks.
        """
        pass
    
    
    async def teardown(self):
        """
        Override this method in subclasses to define teardown tasks.
        
        Runs after the task has completed its work even if it was aborted or
        an error occurred.
        """
        pass


    async def run(self):
        """
        Override this method in subclasses to define the task's functionality.
        """
        raise NotImplementedError("Subclasses must implement the run() method.")


    async def start(self):
        """
        Starts the task and manages pausing and aborting.
        """
        self._abort_event.clear()
        try:
            await self.setup()  # Call setup before running the task
            async for step in self.run():
                logger.debug(f"Task {self.__class__.__name__} step: {step}")
                await self.check_control_flags()
        except asyncio.CancelledError:
            print("Task was cancelled.")
        except Exception as e:
            print(f"Task encountered an error: {e}")
        finally:
            await self.teardown()


    async def check_control_flags(self):
        """
        Checks for pause or abort signals and handles them.
        Call this method periodically in the user's task logic.
        """
        if self._abort_event.is_set():
            raise asyncio.CancelledError("Task aborted.")
        await self._pause_event.wait()  # Wait if paused


    def pause(self):
        """
        Pauses the task.
        """
        self._pause_event.clear()


    def resume(self):
        """
        Resumes the task.
        """
        self._pause_event.set()


    def abort(self):
        """
        Aborts the task.
        """
        self._abort_event.set()
        self._pause_event.set()  # Ensure it doesn't stay paused


# Example subclass
class ExampleTask(Task):
    async def run(self):
        for i in range(10):
            await self.check_control_flags()  # Automatically handles pause/abort
            print(f"Running step {i}")
            await asyncio.sleep(1)  # Simulate work
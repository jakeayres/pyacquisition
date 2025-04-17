from ..core.task import Task
import asyncio


class TestTask(Task):
    """
    TestTask is a subclass of Task that runs a test task.
    """
    
    name = "Test Task"

    async def run(self) -> None:
        """
        Run the test task.
        """
        print(f"Running {self.name}...")
        await asyncio.sleep(1)
        yield 'Step 1 completed'
        print(f"Running {self.name}...")
        await asyncio.sleep(1)
        yield 'Step 2 completed'
        print(f"{self.name} completed.")
import pytest
from pyacquisition import Task


def test_task_name():
    class ExampleTask(Task):
        pass

    task = ExampleTask()
    assert task.name == "ExampleTask", "The name property should return the class name."


@pytest.mark.asyncio
async def test_task_pause_resume():
    class ExampleTask(Task):
        async def run(self, experiment=None):
            yield "Step 1"
            yield "Step 2"

    task = ExampleTask()
    task.pause()
    assert not task._pause_event.is_set(), "Task should be paused."
    task.resume()
    assert task._pause_event.is_set(), "Task should be resumed."


@pytest.mark.asyncio
async def test_task_abort():
    class ExampleTask(Task):
        async def run(self, experiment=None):
            yield "Step 1"

    task = ExampleTask()
    task.abort()
    assert task._abort_event.is_set(), "Task should be aborted."
    assert task._pause_event.is_set(), "Pause event should be set when aborted."


@pytest.mark.asyncio
async def test_task_start():
    class ExampleTask(Task):
        async def setup(self, experiment=None):
            self.setup_called = True

        async def run(self, experiment=None):
            yield "Running step"

        async def teardown(self, experiment=None):
            self.teardown_called = True

    task = ExampleTask()
    task.setup_called = False
    task.teardown_called = False
    await task.start()
    assert task.setup_called, "Setup should be called during start."
    assert task.teardown_called, "Teardown should be called after start."

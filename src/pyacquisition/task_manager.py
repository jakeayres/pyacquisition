import asyncio

from .logger import logger
from .inspectable_queue import InspectableQueue



class TaskManager:
    """
    TaskManager is a class that manages a queue of tasks. It is used by the
    Experiment class to manage the user-defined tasks."
    """

    def __init__(self):

        self._current_task = None
        self._task_queue = InspectableQueue()
        self._running = True



    async def add_task(self, task):
        """
        Add a task to the end of the task queue

        :param      task:  The task
        :type       task:  { type_description }
        """
        await self._task_queue.put(task)
        logger.info(f'Task added: {task.string()}')


    async def get_task(self):
        """
        Get and return the next task from the queue

        :returns:   The task.
        :rtype:     { return_type_description }
        """
        task = await self._task_queue.get()
        logger.info(f'Task retrieved: {task.string()}')
        return task


    def remove_task(self, index):
        """
        Removes a task from the queue at provided index

        :param      index:  The index
        :type       index:  { type_description }
        """
        task = self._task_queue.remove(index)
        logger.info(f'Task removed: {task.string()}')


    def insert_task(self, task, index):
        """
        Insert a task into the queue at the provided index

        :param      task:   The task
        :type       task:   { type_description }
        :param      index:  The index
        :type       index:  { type_description }
        """
        task = self._task_queue.insert(task, index)
        logger.info(f'Task inserted: {task.string()} to {index}')


    def list_tasks(self):
        """
        Return a list of task descriptions (not the objects themselves)

        :returns:   { description_of_the_return_value }
        :rtype:     { return_type_description }
        """
        return [t.string() for t in self._task_queue.inspect()]


    def clear_tasks(self):
        """
        Clear all tasks from the queue
        """
        self._task_queue.clear()
        logger.info(f'All tasks cleared')


    def pause_task(self):
        """
        Pause the current task
        """
        self._current_task.pause()
        logger.info(f'Experiment paused')


    def resume_task(self):
        """
        Resume the current task
        """
        self._current_task.resume()
        logger.info(f'Experiment resumed')


    async def execute_task(self, task):
        """
        Execute the provided task

        :param      task:  The task
        :type       task:  { type_description }
        """
        try:
            await task.execute()
        except Exception as e:
            logger.error(f'Error in task: {task.string()}')
            logger.error(f'Exception raised executing task')
            print(f'Exception raised executing task')
            print(e)
            self.pause_task()
        finally:
            logger.info(f'Task finished: {task.string()}')


    def abort_task(self):
        """
        Abort the current task and proceed
        """
        self._current_task.abort()
        logger.info(f'Current task aborted')


    async def execute(self):
        """
        The main coroutine to run that handles the execution of
        tasks from the task_queue.
        """
        
        while self._running:

            self._current_task = None
            self._current_task = await self.get_task()
            await self.execute_task(self._current_task)
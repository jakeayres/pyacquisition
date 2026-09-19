import asyncio
import uuid
from ..logging import logger
from contextlib import asynccontextmanager
from dataclasses import dataclass, fields
from inspect import Signature, Parameter


@dataclass
class Task:
    """Base class for tasks in the experiment framework."""

    @property
    def name(self) -> str:
        """
        Returns the name of the task.

        This can be overridden in subclasses to provide a custom name for the task.
        """
        return self.__class__.__name__

    def __post_init__(self):
        # Tasks are dataclasses, so two with the same inputs are equal. The id tells
        # them apart, which is how one task in a queue is picked out.
        self._id: str = uuid.uuid4().hex
        self._pause_event: asyncio.Event = asyncio.Event()
        self._abort_event: asyncio.Event = asyncio.Event()
        self._is_paused: bool = False
        self._status: str = "running"
        self._experiment = None
        self._active_subtasks: list[Task] = []
        self._pause_event.set()  # Set to allow task to run immediately
        self._abort_event.clear()  # Clear to allow task to run immediately

    async def setup(self, experiment=None):
        """
        Override this method in subclasses to define setup tasks.
        """
        pass

    async def teardown(self, experiment=None):
        """
        Override this method in subclasses to define teardown tasks.

        Runs after the task has completed its work even if it was aborted or
        an error occurred.
        """
        pass

    async def run(self, experiment=None):
        """
        Override this method in subclasses to define the task's functionality.
        """
        raise NotImplementedError("Subclasses must implement the run() method.")

    async def start(self, experiment=None):
        """
        Starts the task and manages pausing and aborting.
        """
        self._abort_event.clear()
        self._experiment = experiment
        try:
            logger.info(f"[{self.name}] Starting task.")
            await self.setup(experiment=experiment)
            async for step in self.run(experiment=experiment):
                if step:
                    logger.info(f"[{self.name}] {step}")
                await self._check_control_flags()
        except asyncio.CancelledError:
            print("Task was cancelled.")
        except Exception as e:
            print(f"Task encountered an error: {e}")
        finally:
            await self.teardown(experiment=experiment)
            logger.info(f"[{self.name}] Task completed.")

    async def run_subtask(self, subtask: "Task", experiment=None):
        """
        Runs another task as part of this one. Call it with `await` from inside `run()`.

        The subtask goes through its full lifecycle: `setup()`, `run()` and then
        `teardown()`, which runs even if the subtask is aborted or fails. Its steps
        are logged under its own name.

        Pausing or aborting this task also pauses or aborts the subtask, at any
        depth, at the subtask's next step. An abort raises out of this call, so
        the rest of this task's `run()` is skipped. Aborting the subtask directly
        aborts this task too, since it cannot continue without it.

        Errors in the subtask are raised here. Wrap the call in `try`/`except` to
        carry on regardless.

        This task's own `run()` must still be an async generator, so `yield` between
        subtasks (`yield None` if there is nothing to log).

        To run several subtasks at the same time, see `run_subtasks()` and
        `alongside()`.

        Args:
            subtask (Task): The task to run.
            experiment: The experiment to pass to the subtask. Defaults to the
                experiment this task was started with.

        Example:
            async def run(self, experiment):
                await self.run_subtask(WaitFor(minutes=5))
                yield "Waited"
                await self.run_subtask(NewFile(title="after wait"))
                yield "New file"
        """
        if experiment is None:
            experiment = self._experiment

        # Do not begin if this task has already been aborted or is paused.
        await self._check_control_flags()

        self._adopt([subtask])
        await self._execute_subtask(subtask, experiment)

    async def run_subtasks(self, *subtasks: "Task", experiment=None):
        """
        Runs several tasks at the same time, and waits until all of them have finished.
        Call it with `await` from inside `run()`.

        Each subtask goes through its full lifecycle, as with `run_subtask()`. Pausing
        or aborting this task pauses or aborts all of them.

        If one subtask fails or is aborted, the others are aborted (each finishes its
        current step and runs its `teardown()`), and then the error is raised here.
        Aborting one subtask directly therefore aborts this task too. If several
        fail, the first error is raised and the rest are logged.

        The subtasks take turns on one thread, switching only when one of them
        `await`s. A subtask that never awaits, or that blocks for a long time, holds
        up the others.

        Args:
            *subtasks (Task): The tasks to run. Each must be a different task object.
            experiment: The experiment to pass to the subtasks. Defaults to the
                experiment this task was started with.

        Example:
            async def run(self, experiment):
                await self.run_subtasks(RampMagnet(field=5), RampTemperature(kelvin=2))
                yield "Both ramps finished"
        """
        if experiment is None:
            experiment = self._experiment
        if not subtasks:
            return

        await self._check_control_flags()

        self._adopt(subtasks)
        runners = {
            asyncio.create_task(self._execute_subtask(subtask, experiment)): subtask
            for subtask in subtasks
        }
        pending = set(runners)
        failed = []
        try:
            while pending and not failed:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                # An abort ends a runner as cancelled, an error as an exception.
                failed = [r for r in done if r.cancelled() or r.exception()]

            # One has failed: stop the others, and wait for them to clean up.
            for runner in pending:
                runners[runner].abort()
            stopped = await asyncio.gather(*pending, return_exceptions=True)
        except BaseException:
            # This task itself is being cancelled from outside.
            for runner in pending:
                runner.cancel()
            raise
        finally:
            for subtask in subtasks:
                self._release(subtask)

        errors = [r.exception() for r in failed if not r.cancelled()]
        errors += [s for s in stopped if isinstance(s, Exception)]
        for error in errors[1:]:
            logger.error(f"[{self.name}] Another subtask also failed: {error}")
        if errors:
            raise errors[0]
        if failed:
            raise asyncio.CancelledError("Task aborted.")

    @asynccontextmanager
    async def alongside(self, *subtasks: "Task", experiment=None):
        """
        Runs tasks in the background for as long as a block of code runs. Use it
        with `async with` inside `run()`.

        The subtasks start when the block starts, and are aborted when it ends (each
        finishes its current step and runs its `teardown()`, and the block waits for
        that). Use it for things that run continuously, such as a control loop,
        while the block does the main work.

        - Pausing or aborting this task pauses or aborts them too.
        - Aborting one of them directly stops only that one. The block carries on.
        - If one raises an error, the block is interrupted, the others are aborted,
          and the error is raised here. Wrap the `async with` in `try`/`except` to
          carry on regardless.

        The subtasks take turns on one thread, switching only when one of them
        `await`s. A background task should `yield` and `await` regularly, so that it
        can be stopped promptly and does not hold up the block.

        Args:
            *subtasks (Task): The tasks to run in the background. Each must be a
                different task object.
            experiment: The experiment to pass to the subtasks. Defaults to the
                experiment this task was started with.

        Example:
            async def run(self, experiment):
                async with self.alongside(HoldTemperature(kelvin=4.2)):
                    await self.run_subtask(SweepField(target=5))
                    yield "Swept"
                yield "The temperature control has stopped"
        """
        if experiment is None:
            experiment = self._experiment

        await self._check_control_flags()

        failures = []
        aborted_by_failure = False

        async def supervise(subtask):
            nonlocal aborted_by_failure
            try:
                await self._execute_subtask(subtask, experiment)
            except asyncio.CancelledError:
                logger.info(f"[{subtask.name}] Stopped.")
            except Exception as e:
                logger.error(
                    f"[{subtask.name}] Failed while running alongside [{self.name}]: {e}"
                )
                failures.append(e)
                if not self._abort_event.is_set():
                    aborted_by_failure = True
                self.abort()  # interrupt the block, and the other subtasks

        self._adopt(subtasks)
        runners = [asyncio.create_task(supervise(subtask)) for subtask in subtasks]
        try:
            yield
        finally:
            for subtask in subtasks:
                subtask.abort()
            await asyncio.gather(*runners, return_exceptions=True)
            for subtask in subtasks:
                self._release(subtask)

            if failures:
                if aborted_by_failure:
                    self._abort_event.clear()  # the failure, not an abort, is what stops us
                raise failures[0]

    def _adopt(self, subtasks) -> None:
        """
        Registers subtasks that are about to run, so that pausing or aborting this
        task reaches them, and clears any earlier abort.
        """
        running = list(self._active_subtasks)
        for subtask in subtasks:
            if any(subtask is other for other in running):
                raise ValueError(
                    f"[{subtask.name}] is already running as a subtask of [{self.name}]."
                )
            running.append(subtask)
        for subtask in subtasks:
            subtask._abort_event.clear()
            self._active_subtasks.append(subtask)

    def _release(self, subtask: "Task") -> None:
        """
        Forgets a subtask that has finished. It is safe to call more than once.
        """
        # Tasks are dataclasses, which compare equal by value, so compare identity.
        self._active_subtasks = [t for t in self._active_subtasks if t is not subtask]

    async def _execute_subtask(self, subtask: "Task", experiment) -> None:
        """
        Runs the lifecycle of a subtask that has been adopted.
        """
        try:
            logger.info(f"[{subtask.name}] Starting subtask of [{self.name}].")
            await subtask.setup(experiment=experiment)
            async for step in subtask.run(experiment=experiment):
                if step:
                    logger.info(f"[{subtask.name}] {step}")
                await self._check_control_flags()
                await subtask._check_control_flags()
        finally:
            self._release(subtask)
            await subtask.teardown(experiment=experiment)
            logger.info(f"[{subtask.name}] Subtask completed.")

    async def _check_control_flags(self):
        """
        Checks for pause or abort signals and handles them.
        Call this method periodically in the user's task logic.
        """
        if self._abort_event.is_set():
            raise asyncio.CancelledError("Task aborted.")
        await self._pause_event.wait()
        if self._abort_event.is_set():  # aborted while paused
            raise asyncio.CancelledError("Task aborted.")

    @property
    def description(self) -> str:
        """
        Returns a description of the task.
        """
        None

    @property
    def parameters(self) -> dict:
        """
        Returns the displayed parameters of the task.
        """
        None

    def display_dict(self) -> dict:
        """
        Converts the task to a dictionary representation.

        Returns:
            dict: Dictionary representation of the task.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def pause(self):
        """
        Pauses the task, and any subtasks it is currently running.
        """
        self._pause_event.clear()
        for subtask in list(self._active_subtasks):
            subtask.pause()

    def resume(self):
        """
        Resumes the task, and any subtasks it is currently running.
        """
        self._pause_event.set()
        for subtask in list(self._active_subtasks):
            subtask.resume()

    def abort(self):
        """
        Aborts the task, and any subtasks it is currently running.
        """
        self._abort_event.set()
        self._pause_event.set()  # Ensure it doesn't stay paused
        for subtask in list(self._active_subtasks):
            subtask.abort()

    @classmethod
    def register_endpoints(
        cls,
        experiment,
        label=None,
        task_manager=None,
        tasks_path="/tasks",
        **fixed_kwargs,
    ):
        """
        Register the task endpoints with the API server.

        Manually build the endpoint annotations and signature based on the dataclass fields
        and add the endpoint functionanlly in order to dynamically create the endpoint with
        the parameters and type hints.

        Args:
            experiment: The experiment instance to register the endpoints with.
            label (str | None): The name of the endpoint. Defaults to the class name.
            task_manager (TaskManager | None): The task manager that the endpoint
                queues the task on. Defaults to the experiment's main task manager.
            tasks_path (str): The path the endpoint is placed under.
            **fixed_kwargs: Values for the task's inputs that are fixed, and so are
                not offered by the endpoint.
        """

        fields_dict = {field.name: field.type for field in fields(cls)}
        params = [
            Parameter(name, Parameter.POSITIONAL_OR_KEYWORD, annotation=type_)
            for name, type_ in fields_dict.items()
            if name not in fixed_kwargs
        ]

        async def task_endpoint(**kwargs):
            """
            Endpoint to run the task.

            Returns:
                dict: The result of the task.
            """
            task = cls(**fixed_kwargs, **kwargs)
            queue = (
                task_manager if task_manager is not None else experiment._task_manager
            )
            queue.add_task(task)
            return {"status": 200, "message": f"{cls.__name__} added"}

        if label is not None:
            task_endpoint.__name__ = f"{label}"
            endpoint_path = f"{tasks_path}/{label.lower().replace(' ', '_')}"
        else:
            task_endpoint.__name__ = f"{cls.__name__}"
            endpoint_path = f"{tasks_path}/{cls.__name__.lower().replace(' ', '_')}"
        task_endpoint.__annotations__ = fields_dict
        task_endpoint.__annotations__["return"] = dict
        task_endpoint.__signature__ = Signature(
            parameters=params, return_annotation=dict
        )
        task_endpoint.__doc__ = (
            cls.__doc__.split("\n")[0] if cls.__doc__ else "No help available."
        )

        experiment._api_server.app.add_api_route(
            endpoint_path,
            task_endpoint,
            methods=["GET"],
            tags=["tasks"],
        )

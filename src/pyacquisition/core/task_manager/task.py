import asyncio
import inspect
import time
import traceback
import uuid
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from inspect import Signature
from typing import ClassVar

from fastapi import HTTPException

from ..instrument import resolve_enum_kwargs
from ..logging import logger
from .inputs import input_parameters

# Runners that have been cancelled. Several tasks can share one runner (a subtask
# that runs inside its parent does), so a cancel is sent once, however many of them
# are aborted. A second cancel would land in the middle of the clean-up.
_cancelled = weakref.WeakSet()


def _cancel(runner) -> None:
    """Cancels the asyncio task that is running a task, once."""
    if runner is None or runner.done() or runner in _cancelled:
        return
    try:
        current = asyncio.current_task()
    except RuntimeError:  # no event loop is running
        current = None
    if runner is current:
        # Called from the task's own code. The flag is seen at the next checkpoint,
        # and a cancel now would only be delivered late, in the clean-up.
        return
    _cancelled.add(runner)
    runner.cancel()


def _consume_cancel() -> None:
    """Forgets the cancels that were requested of the current asyncio task, which
    the caller has dealt with, so that they do not affect what runs next and a
    later abort is sent."""
    task = asyncio.current_task()
    while task is not None and task.cancelling():
        task.uncancel()
    _cancelled.discard(task)


@dataclass
class Task:
    """Base class for tasks in the experiment framework.

    A task does its work in `run()`, which is an `async` method. Inside it, wait
    with `self.sleep()`, `self.wait_until()` or `self.checkpoint()`, and it can be
    paused and aborted there, however deep in your own helper methods it is.

    Override `setup()`, `run()` and `teardown()`, and, if pausing should do
    something to your hardware, `on_pause()` and `on_resume()`.

    Example:
        @dataclass
        class RampMagnet(Task):
            \"\"\"Sweep the magnet to a field.\"\"\"

            magnet: str
            field: float

            async def run(self, experiment):
                psu = experiment.instruments[self.magnet]
                psu.set_target_field(self.field)
                psu.to_setpoint()
                await self.wait_until(lambda: psu.get_sweep_status() == REST)

            def on_pause(self, experiment):
                experiment.instruments[self.magnet].hold()

            def on_resume(self, experiment):
                experiment.instruments[self.magnet].to_setpoint()

            async def teardown(self, experiment):
                experiment.instruments[self.magnet].hold()
    """

    # The instruments that a task that comes with pyacquisition is for, so that it
    # is registered by itself when they are present. It maps the name of the input
    # that holds an instrument's id to the instrument classes that will do:
    #     applies_to = {"lakeshore": (Lakeshore_340, Lakeshore_350)}
    # It is used only by those tasks. Register your own with `register_task()`.
    applies_to: ClassVar[dict | None] = None

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
        self._paused_event: asyncio.Event = asyncio.Event()  # set while paused
        self._abort_event: asyncio.Event = asyncio.Event()
        self._is_paused: bool = False
        self._status: str = "running"
        self._experiment = None
        self._active_subtasks: list[Task] = []
        # Where the task is in its life: "idle", "setup", "run" or "teardown".
        # Pause and abort are not honoured in a teardown, which must always finish.
        self._phase: str = "idle"
        self._runner = None  # the asyncio task that is running this task
        self._outcome: str | None = None
        self._failure: BaseException | None = None
        self._hook_failure: BaseException | None = None
        self._pause_hook_ran: bool = False
        # How long it has been running, and how far along it is (see `progress`).
        self._started_at: float | None = None  # wall clock, when it started
        self._clock_start: float | None = None  # monotonic, when it started
        self._paused_for: float = 0.0  # seconds spent paused so far
        self._paused_since: float | None = None
        self._progress: dict | None = None
        self._pause_event.set()  # Set to allow task to run immediately
        self._abort_event.clear()  # Clear to allow task to run immediately

    # ------------------------------------------------------------------ hooks
    async def setup(self, experiment=None):
        """
        Override this method in subclasses to define setup tasks.
        """
        pass

    async def teardown(self, experiment=None):
        """
        Override this method in subclasses to define teardown tasks.

        Runs after the task has completed its work even if it was aborted or
        an error occurred. It is never paused or aborted, so it can be used to put
        an instrument into a safe state. `self.sleep()` and the other waits do not
        stop for a pause or abort in here.
        """
        pass

    async def run(self, experiment=None):
        """
        Override this method in subclasses to define the task's functionality.

        Write it as an ordinary `async def`. Wait with `await self.sleep()`,
        `await self.wait_until()` and `await self.checkpoint()`, because the task
        can be paused and aborted there. It also works as an async generator that
        `yield`s a message, or `None`, at each place it can be paused.
        """
        raise NotImplementedError("Subclasses must implement the run() method.")

    def on_pause(self, experiment=None):
        """
        Override this method to do something when the task is paused, such as
        putting an instrument on hold.

        It is called at once, when the pause is requested, and not when the task
        next reaches a checkpoint. It is an ordinary method, like the instruments'.
        It is called only while `run()` is in progress, and once for each pause.
        A running subtask gets its own call, so the task that owns the hardware
        decides what pausing means, and a task made of subtasks needs no hook.

        If it raises an error, the task fails. Nothing further is done for it.
        """
        pass

    def on_resume(self, experiment=None):
        """
        Override this method to undo what `on_pause()` did, such as sending an
        instrument on its way again.

        It is called before the task carries on, so it can check the state of the
        hardware first. If it raises an error, the task does not carry on: it fails,
        and `teardown()` runs.
        """
        pass

    # ------------------------------------------------------------ the toolkit
    def log(self, message, level: str = "info") -> None:
        """
        Logs a message under the name of the task. It is shown in the interface.

        Args:
            message: What to say.
            level (str): `"info"` (the default), `"debug"`, `"warning"` or `"error"`.
        """
        getattr(logger, level)(f"[{self.name}] {message}")

    async def checkpoint(self) -> None:
        """
        A place where the task can be paused or aborted.

        Blocks while the task is paused, and raises to end the task if it has been
        aborted. `sleep()`, `wait_until()` and `run_subtask()` are checkpoints, so
        it is only needed in a loop of your own that calls none of them.
        """
        await self._check_control_flags()

    async def sleep(self, seconds: float) -> None:
        """
        Waits, and is a checkpoint.

        While the task is paused the time does not pass, so `sleep(300)` is five
        minutes of running time. It ends at once if the task is aborted. Code after
        it does not run while the task is paused.

        Args:
            seconds (float): How long to wait.
        """
        if self._phase == "teardown":
            await asyncio.sleep(seconds)
            return

        loop = asyncio.get_running_loop()
        remaining = float(seconds)
        if remaining <= 0:
            await asyncio.sleep(0)
        while remaining > 0:
            await self._check_control_flags()
            started = loop.time()
            try:
                await asyncio.wait_for(self._paused_event.wait(), timeout=remaining)
            except TimeoutError:
                break  # the whole time has passed without a pause
            remaining -= loop.time() - started  # paused: hold the rest until resumed
        await self._check_control_flags()

    async def wait_until(
        self, condition, poll: float = 1.0, timeout: float | None = None, what=None
    ) -> None:
        """
        Waits until something is true, checking it every `poll` seconds. It is a
        checkpoint each time, so the task can be paused and aborted while it waits.

        The condition is not checked while the task is paused, and the time spent
        paused does not count towards `timeout`.

        Args:
            condition: A function that returns whether to stop waiting. It may be
                an `async` function.
            poll (float): Seconds between checks.
            timeout (float | None): Give up after this many seconds of running time.
            what (str | None): What was being waited for, for the error message.

        Raises:
            TimeoutError: If the condition is still false after `timeout`.

        Example:
            await self.wait_until(lambda: psu.get_sweep_status() == ModeStatusN.REST)
        """
        waited = 0.0
        while True:
            await self._check_control_flags()
            result = condition()
            if inspect.isawaitable(result):
                result = await result
            if result:
                return
            if timeout is not None and waited >= timeout:
                raise TimeoutError(
                    f"Timed out after {timeout} s waiting for "
                    f"{what or 'the condition'}."
                )
            step = poll if timeout is None else min(poll, timeout - waited)
            await self.sleep(step)
            waited += step

    def set_progress(
        self,
        done: float,
        of: float | None = None,
        *,
        remaining: float | None = None,
        note: str | None = None,
    ) -> None:
        """
        Says how far along the task is, for the interface to show. Call it as the
        task goes.

        Args:
            done (float): A fraction from 0 to 1, or with `of`, the steps done.
            of (float | None): How many steps there are, so the interface shows
                "3 of 10".
            remaining (float | None): Seconds left, where the task knows (a wait
                does). Otherwise the interface estimates it from the time so far.
            note (str | None): What it is doing now, such as "Sweeping to 2 T".

        Example:
            for i, kelvin in enumerate(points):
                self.set_progress(i, of=len(points), note=f"Going to {kelvin} K")
                ...
        """
        fraction = done / of if of else done
        self._progress = {
            "fraction": min(1.0, max(0.0, float(fraction))),
            "step": done if of else None,
            "steps": of,
            "remaining": remaining,
            "note": note,
            "at": self.elapsed,  # the running time when this was said
        }

    @property
    def elapsed(self) -> float | None:
        """Seconds the task has been running, not counting time spent paused, or
        None if it hasn't started."""
        if self._clock_start is None:
            return None
        now = time.monotonic()
        paused = self._paused_for
        if self._paused_since is not None:
            paused += now - self._paused_since
        return max(0.0, now - self._clock_start - paused)

    @property
    def progress(self) -> dict | None:
        """How far along the task is, as the interface shows it: `fraction` (0 to
        1), `step` and `steps` if it counts steps, `remaining` seconds if it said
        (counted down since), and `note`. None if it hasn't said."""
        if self._progress is None:
            return None
        shown = {k: v for k, v in self._progress.items() if k != "at"}
        if shown["remaining"] is not None and self._progress["at"] is not None:
            since = (self.elapsed or 0.0) - self._progress["at"]
            shown["remaining"] = max(0.0, shown["remaining"] - since)
        return shown

    def timing(self) -> dict:
        """When the task started, how long it has run, how far along it is, and
        the same for the subtasks it is running now, for the interface."""
        return {
            "started_at": self._started_at,
            "elapsed": self.elapsed,
            "progress": self.progress,
            "subtasks": [
                {"name": subtask.name, "progress": subtask.progress}
                for subtask in self._active_subtasks
            ],
        }

    def expect(self, actual, wanted, what: str = "Value", tolerance=None):
        """
        Checks a value, such as an instrument's status or the read-back of a
        setting, and raises if it is not what was wanted. If it is, that is logged.

        Args:
            actual: The value that was found.
            wanted: The value that was needed.
            what (str): What is being checked, for the message.
            tolerance: If given, numbers within this of each other match. Left out,
                the values must be equal.

        Returns:
            The value that was found.

        Raises:
            ValueError: If the value is not the one that was wanted.

        Example:
            self.expect(psu.get_activity_status(), ActivityStatus.HOLD, "Activity")
        """

        def shown(value):
            return value.name if isinstance(value, Enum) else value

        if tolerance is None:
            matches = actual == wanted
        else:
            matches = abs(actual - wanted) <= tolerance
        if not matches:
            raise ValueError(f"{what}: expected {shown(wanted)}, got {shown(actual)}")
        self.log(f"{what}: {shown(actual)} OK")
        return actual

    # ------------------------------------------------------------- lifecycle
    @property
    def outcome(self) -> str | None:
        """How the task ended: `"completed"`, `"failed"` or `"aborted"`. It is
        `None` until it has ended."""
        return self._outcome

    @property
    def failure(self) -> BaseException | None:
        """The error that made the task fail, if it did."""
        return self._failure

    @property
    def paused(self) -> bool:
        """Whether the task is paused."""
        return not self._pause_event.is_set()

    async def start(self, experiment=None):
        """
        Runs the task: `setup()`, `run()` and `teardown()`. It does not raise if the
        task fails or is aborted. Check `outcome` and `failure` for how it went.
        """
        self._abort_event.clear()
        self._experiment = experiment
        self._outcome = self._failure = self._hook_failure = None

        # The task runs in an asyncio task of its own, so that an abort can cancel it
        # wherever it is waiting.
        runner = asyncio.ensure_future(self._lifecycle(experiment))
        self._runner = runner
        try:
            await runner
        except asyncio.CancelledError:
            if not runner.cancelled() or asyncio.current_task().cancelling():
                raise  # this is being cancelled itself
            self._outcome = "aborted"  # it was cancelled before it began
            return
        # If this is cancelled, the cancel is passed to the runner, which deals with
        # it and ends normally. Whatever is running this still needs to be told.
        if asyncio.current_task().cancelling():
            raise asyncio.CancelledError

    async def _lifecycle(self, experiment):
        """Runs the task and records how it ended. Never raises."""
        self._runner = asyncio.current_task()
        try:
            logger.info(f"[{self.name}] Starting task.")
            await self._execute(experiment)
            self._outcome = "completed"
            logger.info(f"[{self.name}] Task completed.")
        except asyncio.CancelledError:
            _consume_cancel()
            if self._hook_failure is not None:
                self._fail(self._hook_failure)
            else:
                self._outcome = "aborted"
                logger.info(f"[{self.name}] Task aborted.")
        except Exception as e:
            _consume_cancel()
            self._fail(e)
        finally:
            self._runner = None

    def _fail(self, error: BaseException) -> None:
        self._outcome = "failed"
        self._failure = error
        logger.error(f"[{self.name}] Task failed: {type(error).__name__}: {error}")
        logger.debug("".join(traceback.format_exception(error)))

    async def _execute(self, experiment):
        """
        Runs `setup()`, `run()` and then `teardown()`, which runs however `run()`
        ended. An error in `setup()` or `run()`, or an abort, is raised after the
        teardown.
        """
        # The clock starts, and any progress from an earlier run is forgotten.
        self._started_at = time.time()
        self._clock_start = time.monotonic()
        self._paused_for = 0.0
        self._paused_since = time.monotonic() if self.paused else None
        self._progress = None
        try:
            self._phase = "setup"
            await self.setup(experiment=experiment)
            self._phase = "run"
            # A pause that arrived during the setup holds the task here.
            await self._check_control_flags()
            await self._run_body(experiment)
        except BaseException:
            await self._teardown(experiment, raise_errors=False)
            raise
        await self._teardown(experiment, raise_errors=True)

    async def _teardown(self, experiment, raise_errors: bool):
        self._phase = "teardown"
        try:
            await self.teardown(experiment=experiment)
        except Exception as e:
            if raise_errors:
                raise
            # The task is ending in an error already, which is the one to report.
            logger.error(f"[{self.name}] Teardown failed as well: {e}")
        finally:
            self._phase = "idle"

    async def _run_body(self, experiment):
        """Runs `run()`, whether it is an `async def` or an async generator."""
        result = self.run(experiment=experiment)
        if not inspect.isasyncgen(result):
            await result
            return
        try:
            async for step in result:
                if step:
                    logger.info(f"[{self.name}] {step}")
                await self._check_control_flags()
        finally:
            # Finish the generator now, so that its own clean-up runs before
            # `teardown()` and not whenever it is garbage collected.
            await result.aclose()

    async def run_subtask(self, subtask: "Task", experiment=None):
        """
        Runs another task as part of this one. Call it with `await` from inside `run()`.

        The subtask goes through its full lifecycle: `setup()`, `run()` and then
        `teardown()`, which runs even if the subtask is aborted or fails. Its steps
        are logged under its own name.

        Pausing or aborting this task also pauses or aborts the subtask, at any
        depth. A pause calls the subtask's `on_pause()`. An abort ends the subtask
        wherever it is waiting, and raises out of this call, so the rest of this
        task's `run()` is skipped. Aborting the subtask directly aborts this task
        too, since it cannot continue without it.

        Errors in the subtask are raised here. Wrap the call in `try`/`except` to
        carry on regardless.

        To run several subtasks at the same time, see `run_subtasks()` and
        `alongside()`.

        Args:
            subtask (Task): The task to run.
            experiment: The experiment to pass to the subtask. Defaults to the
                experiment this task was started with.

        Example:
            async def run(self, experiment):
                await self.run_subtask(WaitFor(minutes=5))
                await self.run_subtask(NewFile(file_name="after wait"))
        """
        if experiment is None:
            experiment = self._experiment

        # Do not begin if this task has already been aborted or is paused.
        await self._check_control_flags()

        self._adopt([subtask])
        try:
            await self._execute_subtask(subtask, experiment)
        except asyncio.CancelledError:
            self.abort()  # a subtask that is aborted takes this task with it
            raise

    async def run_subtasks(self, *subtasks: "Task", experiment=None):
        """
        Runs several tasks at the same time, and waits until all of them have finished.
        Call it with `await` from inside `run()`.

        Each subtask goes through its full lifecycle, as with `run_subtask()`. Pausing
        or aborting this task pauses or aborts all of them.

        If one subtask fails or is aborted, the others are aborted (each runs its
        `teardown()`), and then the error is raised here. Aborting one subtask
        directly therefore aborts this task too. If several fail, the first error
        is raised and the rest are logged.

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
                _cancel(runner)
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
        runs its `teardown()`, and the block waits for that). Use it for things that
        run continuously, such as a control loop, while the block does the main work.

        - Pausing or aborting this task pauses or aborts them too.
        - Aborting one of them directly stops only that one. The block carries on.
        - If one raises an error, the block is interrupted, the others are aborted,
          and the error is raised here. Wrap the `async with` in `try`/`except` to
          carry on regardless.

        The subtasks take turns on one thread, switching only when one of them
        `await`s. A background task should wait with `self.sleep()` regularly, so
        that it can be stopped promptly and does not hold up the block.

        Args:
            *subtasks (Task): The tasks to run in the background. Each must be a
                different task object.
            experiment: The experiment to pass to the subtasks. Defaults to the
                experiment this task was started with.

        Example:
            async def run(self, experiment):
                async with self.alongside(HoldTemperature(kelvin=4.2)):
                    await self.run_subtask(SweepField(target=5))
                self.log("The temperature control has stopped")
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
                    _consume_cancel()
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
            subtask._hook_failure = None
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
        # The subtask may run subtasks of its own, and they take the experiment from it.
        subtask._experiment = experiment
        # It runs in whichever asyncio task is running this, so that aborting it
        # cancels that.
        subtask._runner = asyncio.current_task()
        try:
            logger.info(f"[{subtask.name}] Starting subtask of [{self.name}].")
            await subtask._execute(experiment)
        except asyncio.CancelledError:
            if subtask._hook_failure is not None:
                # It was stopped by an error in one of its hooks: raise that.
                _consume_cancel()
                raise subtask._hook_failure from None
            raise
        finally:
            subtask._runner = None
            self._release(subtask)
            logger.info(f"[{subtask.name}] Subtask completed.")

    async def _check_control_flags(self):
        """
        Checks for pause or abort signals and handles them: raises if the task has
        been aborted, and waits while it is paused. A teardown is never held up.
        """
        if self._phase == "teardown":
            return
        if self._abort_event.is_set():
            raise asyncio.CancelledError("Task aborted.")
        await self._pause_event.wait()
        if self._abort_event.is_set():  # aborted while paused
            raise asyncio.CancelledError("Task aborted.")

    # --------------------------------------------------------------- display
    @property
    def description(self) -> str | None:
        """
        Returns a description of the task. It is the first line of the docstring
        unless overridden.
        """
        doc = type(self).__doc__
        if type(self) is Task or not doc:
            return None
        first = inspect.cleandoc(doc).split("\n")[0].strip()
        if first.startswith(f"{type(self).__name__}("):
            return None  # the one that `@dataclass` writes when there is no docstring
        return first or None

    @property
    def parameters(self) -> dict | None:
        """
        Returns the displayed parameters of the task. They are its inputs unless
        overridden.
        """
        if not is_dataclass(self):
            return None
        return {f.name: getattr(self, f.name) for f in fields(self)} or None

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

    # ------------------------------------------------- pause, resume, abort
    def pause(self):
        """
        Pauses the task, and any subtasks it is currently running.

        `on_pause()` is called at once, for each running subtask and then for this
        task. The task stops at its next checkpoint. A task that is being aborted
        ignores it.
        """
        if self._abort_event.is_set() or not self._pause_event.is_set():
            return
        self._pause_event.clear()
        self._paused_event.set()
        self._is_paused = True
        self._paused_since = time.monotonic()
        for subtask in list(self._active_subtasks):
            subtask.pause()
        if self._phase == "run":
            self._pause_hook_ran = True
            self._call_hook(self.on_pause)

    def resume(self):
        """
        Resumes the task, and any subtasks it is currently running.

        `on_resume()` is called first, for this task and then for each running
        subtask, and only then does the task carry on. If one of them raises an
        error the task fails instead.
        """
        if self._pause_event.is_set() or self._abort_event.is_set():
            return
        if self._pause_hook_ran:
            self._pause_hook_ran = False
            if not self._call_hook(self.on_resume):
                return
        for subtask in list(self._active_subtasks):
            subtask.resume()
        if self._abort_event.is_set():  # a subtask's hook failed, which aborted us
            return
        self._is_paused = False
        self._stop_pause_clock()
        self._paused_event.clear()
        self._pause_event.set()

    def _stop_pause_clock(self) -> None:
        """Adds the time since it was paused to the time spent paused."""
        if self._paused_since is not None:
            self._paused_for += time.monotonic() - self._paused_since
            self._paused_since = None

    def abort(self):
        """
        Aborts the task, and any subtasks it is currently running.

        The task stops wherever it is waiting, then `teardown()` runs. Aborting a
        task that is already being aborted does nothing.
        """
        if self._abort_event.is_set():
            return
        self._abort_event.set()
        self._pause_event.set()  # Ensure it doesn't stay paused
        self._paused_event.clear()
        self._is_paused = False
        self._stop_pause_clock()
        for subtask in list(self._active_subtasks):
            subtask.abort()
        _cancel(self._runner)

    def _call_hook(self, hook) -> bool:
        """Calls `on_pause` or `on_resume`. An error in it fails the task."""
        try:
            hook(self._experiment)
        except Exception as e:
            logger.error(f"[{self.name}] {hook.__name__}() failed: {e}")
            self._hook_failure = e
            self.abort()
            return False
        return True

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

        # Inputs that are fixed for this registration may be text for an enum too.
        fixed_kwargs = resolve_enum_kwargs(cls, fixed_kwargs)
        # Each input with its default, what it is for and any choices, so that a
        # form can be built from the API schema (see inputs.py). An enum is asked
        # for as text (`"OUTPUT_1"`), which is resolved to the member.
        params, fields_dict = input_parameters(cls, experiment, fixed_kwargs)

        async def task_endpoint(**kwargs):
            """
            Endpoint to run the task.

            Returns:
                dict: The result of the task.
            """
            try:
                kwargs = resolve_enum_kwargs(cls, kwargs)
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            try:
                task = cls(**fixed_kwargs, **kwargs)
            except (TypeError, ValueError) as error:
                # A task that checks its inputs as it is made (in __post_init__)
                # says what is wrong with them, which is worth showing as it is.
                raise HTTPException(status_code=422, detail=str(error)) from error
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
            # The task's own name, rather than FastAPI's title case of it
            # ("Waitfor"), for the interfaces' lists of tasks.
            summary=task_endpoint.__name__,
        )

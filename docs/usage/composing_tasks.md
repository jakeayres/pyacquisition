# Composing Tasks

Real procedures are made of stages: start a file, record something, start another file, record something else. Rather than write one long task, write each stage as a small task, and then have a larger task run them in order. Any task can run any other task by calling `await self.run_subtask(...)` from its `run()` method.

## Example: two distributions

Here is a task that records Gaussian random numbers to one file, and then uniform random numbers to another. It is built from three smaller tasks: your own `SampleGaussian` from the [previous page](tasks.md), a `SampleUniform` that is written in just the same way, and the built-in `NewFile`.

First, `SampleUniform`. It is the same as `SampleGaussian` with a different distribution. Add it below `SampleGaussian` in `my_experiment.py`:

```python title="my_experiment.py" linenums="1"
@dataclass
class SampleUniform(Task):
    """Record random numbers from a uniform distribution."""

    low: float
    high: float
    seconds: int = 10

    @property
    def description(self):
        return f"Sample a uniform distribution for {self.seconds} s"

    @property
    def parameters(self):
        return {"low": self.low, "high": self.high}

    async def run(self, experiment):
        rng = experiment.instruments["rng"]
        rng.use_uniform(self.low, self.high)
        yield f"Sampling uniformly between {self.low} and {self.high}"
        for _ in range(self.seconds):
            await asyncio.sleep(1)
            yield None

    async def teardown(self, experiment):
        experiment.instruments["rng"].use_gaussian(0.0, 1.0)
```

Now the task that puts them together. Add it below `SampleUniform`, with the import at the top of the file alongside the others:

```python title="my_experiment.py" linenums="1"
from pyacquisition.tasks import NewFile


@dataclass
class CompareDistributions(Task):
    """Record Gaussian numbers, then uniform numbers, to separate files."""

    seconds: int = 10

    async def run(self, experiment):
        await self.run_subtask(NewFile(file_name="gaussian")) # (1)!
        yield None # (2)!

        await self.run_subtask(
            SampleGaussian(mean=0.0, sigma=1.0, seconds=self.seconds)
        ) # (3)!
        yield "Gaussian numbers recorded"

        await self.run_subtask(NewFile(file_name="uniform"))
        yield None

        await self.run_subtask(
            SampleUniform(low=0.0, high=1.0, seconds=self.seconds)
        )
        yield "Uniform numbers recorded"
```

1. Create the subtask as you would any object, with the inputs it needs, and run it with `await self.run_subtask(...)`. Nothing else is needed to make it work: `NewFile` is already registered, but you do not have to register a task to use it as a subtask.
2. `run()` still has to be a generator, so **yield between subtasks**. Yield `None` if there is nothing to log.
3. Your own tasks work exactly the same way. Subtasks can be given the parent's inputs, so `CompareDistributions` passes its `seconds` on to each of them.

Register it in `setup()`, next to `SampleGaussian`:

```python
self.register_task(CompareDistributions, label="Compare Distributions")
```

Run **Tasks → Compare Distributions** with `seconds` 10. After twenty seconds you have two new data files, `gaussian` and `uniform`, each holding ten seconds of numbers from its own distribution, and **Current Task** in the **Task Queue** window reads `CompareDistributions` throughout. The **Logs** window shows the progress of each stage, labelled with the subtask's own name.

!!! note "Each subtask cleans up after itself"
    `SampleGaussian` ends by running its own `teardown()`, which puts the generator back to its default distribution. That happens as soon as *that subtask* finishes, not when the whole parent does. Here it makes no difference, because the next subtask chooses its own distribution first. Keep it in mind when a subtask's `teardown()` changes something the next stage relies on. In that case, do the clean-up in the parent's `teardown()` instead.

## What `run_subtask()` does

- **The subtask runs completely.** Its `setup()`, `run()` and `teardown()` all run, and its steps are logged under its own name (for example `[SampleGaussian] Sampling a Gaussian with mean 0.0 and sigma 1.0`).
- **Pausing and aborting reach it.** When you pause or abort the parent, whichever subtask is running at that moment pauses or stops too, however deeply subtasks are nested. You can therefore interrupt a long `WaitFor` inside a larger task. When a task is aborted, the running subtask's `teardown()` runs, then the parent's, and the rest of the parent's `run()` is skipped.
- **Nothing starts while paused.** A subtask that has not yet begun will not start while the parent is paused or after it has been aborted.
- **It gets the same experiment.** You do not pass `experiment` on. Subtasks receive the one the parent was given.
- **Errors stop the parent.** If a subtask raises an error, that error is raised at the `await self.run_subtask(...)` line, the parent stops, and both `teardown()` methods run.

## Loops and conditions

A task's `run()` is ordinary Python, so use loops and `if` statements to decide what to run:

```python
@dataclass
class GaussianWidths(Task):
    """Record Gaussian numbers of three different widths, each to its own file."""

    async def run(self, experiment):
        for sigma in [0.5, 1.0, 2.0]:
            await self.run_subtask(NewFile(file_name=f"gaussian sigma {sigma}"))
            yield None
            await self.run_subtask(SampleGaussian(mean=0.0, sigma=sigma))
            yield f"Finished sigma {sigma}"
```

Subtasks can themselves run subtasks, so you can build a procedure up in layers, and reuse the same small tasks in many different larger ones.

## Carrying on after an error

Normally an error in a subtask stops everything. If a stage is optional, catch the error:

```python
try:
    await self.run_subtask(SampleUniform(low=0.0, high=1.0))
except Exception as error:
    yield f"The uniform stage failed, so it was skipped: {error}"
```

Catch `Exception`, as here, and not everything (a bare `except:`). Aborting a task works by raising `asyncio.CancelledError`, which `except Exception` deliberately does not catch. A bare `except:` would catch it, and stop you being able to abort.

!!! warning "Use `run_subtask()`, not `subtask.start()`"
    It is tempting to write `await SampleGaussian(...).start(experiment=experiment)`, but this will not do what you want. A task started that way cannot be paused or aborted through its parent, so aborting the parent has to wait until the whole subtask has finished, and any error in it is swallowed instead of stopping the parent. `run_subtask()` has neither problem.

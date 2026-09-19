# Writing Tasks

A **task** is a procedure that you want to run on your experiment: record data under one condition, wait an hour, start a new file, ramp a temperature. Tasks are run from a queue, one at a time, and can be paused or aborted while they run. You can queue them from the interface, and you can build bigger tasks [out of smaller ones](composing_tasks.md).

## Your first task

Here is a task that makes the random number generator draw from a Gaussian distribution for a number of seconds. Add it to `my_experiment.py`:

```python title="my_experiment.py" linenums="1" hl_lines="1 2 4 9-34 51"
import asyncio
from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.instruments import Clock
from random_number_generator import RandomNumberGenerator


@dataclass # (1)!
class SampleGaussian(Task):
    """Record random numbers from a Gaussian distribution.""" # (2)!

    mean: float # (3)!
    sigma: float
    seconds: int = 10

    @property
    def description(self): # (4)!
        return f"Sample a Gaussian distribution for {self.seconds} s"

    @property
    def parameters(self):
        return {"mean": self.mean, "sigma": self.sigma}

    async def run(self, experiment): # (5)!
        rng = experiment.instruments["rng"] # (6)!
        rng.use_gaussian(self.mean, self.sigma)
        yield f"Sampling a Gaussian with mean {self.mean} and sigma {self.sigma}" # (7)!
        for _ in range(self.seconds):
            await asyncio.sleep(1) # (8)!
            yield None

    async def teardown(self, experiment): # (9)!
        experiment.instruments["rng"].use_gaussian(0.0, 1.0)


class MyExperiment(Experiment):

    def __init__(self):
        super().__init__(data_path="my_data")

    def setup(self):
        clock = Clock("clock")
        rng = RandomNumberGenerator("rng")
        self.add_instrument(clock)
        self.add_instrument(rng)

        self.add_measurement(Measurement("time", clock.time))
        self.add_measurement(Measurement("random", rng.random_number))

        self.register_task(SampleGaussian, label="Sample Gaussian") # (10)!


if __name__ == "__main__":
    MyExperiment().run()
```

1. **Every task class needs the `@dataclass` decorator.** It turns the annotated attributes below into the task's inputs. Without it the task registers with no inputs and fails when it runs.
2. The first line of the docstring is shown in the interface as the description of the task.
3. **Inputs** are annotated attributes. Ones without a default value are required. Use `int`, `float`, `str` or `bool`.
4. Optional, but recommended. `description` and `parameters` are what the **Task Queue** window shows for a task that is waiting, and for the task that is running. Without them it shows `None`. The window is refreshed about once a second, and `parameters` is read each time, so it can return values that change while the task runs, such as the latest reading.
5. `run()` is where the work happens. It is an `async` method that **yields**. Everything you need to know about it is [explained below](#how-run-works).
6. `experiment` is your experiment. `experiment.instruments` is how a task reaches the instruments it controls.
7. Whatever `run()` yields is written to the log. Yield `None` if there is nothing to say.
8. Wait with `await asyncio.sleep(...)`. Never use `time.sleep()` in a task, which would freeze the entire experiment while it waits.
9. `teardown()` always runs when the task ends, including when it was aborted or hit an error. Use it to leave your instruments in a safe state. Here, the generator goes back to its default distribution.
10. Register the task, passing the class itself (not an instance: no brackets). It now appears in the **Tasks** menu. `label` sets the name shown there.

Run the experiment and open **Tasks → Sample Gaussian**. Fill in **every** input, for example `mean` 5, `sigma` 2 and `seconds` 10 (the form starts at zero, and defaults are not filled in for you), then press **Send Request**. The task joins the queue and starts. Open **Plots → New Plot** and watch `random` settle around 5 for ten seconds, then return to a spread around 0 when the task ends. [Running tasks](running_tasks.md) covers what you can do with the queue.

## How `run()` works

`run()` is an **asynchronous generator**. The two things that make it one are the keyword `async` in front of `def`, and `yield` statements inside. You do not need to understand asynchronous programming to write one, but a few rules matter:

- **It must contain at least one `yield`.** Each `yield` is a step. Between steps, `pyacquisition` logs what you yielded, lets the rest of the experiment run (measurements, the interface), and checks whether the task has been paused or aborted. **A task can only be paused or aborted at a `yield`.** A long piece of work with no `yield` in it cannot be interrupted, so yield often, even if it is just `yield None`.
- **Pause with `await asyncio.sleep(seconds)`.** This waits without blocking anything else. Do not use `time.sleep()`.
- **Everything else is ordinary Python.** Loops, conditions, calling instrument methods, and calculations all work as usual. Instrument calls are normal (not `async`) function calls.

## `setup()` and `teardown()`

Tasks have two optional hooks in addition to `run()`:

| Method | Runs | Use it to |
|---|---|---|
| `setup(self, experiment)` | Before `run()` | Prepare the instruments |
| `teardown(self, experiment)` | After `run()`, **always** | Return the instruments to a safe state |

Both are `async def` methods, but ordinary code works inside them. `teardown()` runs when the task finishes normally, when it is aborted, and when it raises an error. If `setup()` raises an error, `run()` is skipped and `teardown()` still runs.

## Registering tasks

Tasks must be registered in `setup()` to appear in the **Tasks** menu:

```python
self.register_task(SampleGaussian, label="Sample Gaussian")
```

| Argument | Effect |
|---|---|
| The class | Required. Pass the class, not an instance. |
| `label` | The name in the menu, and in the API address (`/tasks/sample_gaussian`). Without it the class name is used, run together: `Samplegaussian` and `/tasks/samplegaussian`. |
| Other keywords | Fix an input to a value. The task then appears with that input hidden. |

Fixing inputs lets you offer ready-made variants of a general task:

```python
self.register_task(SampleGaussian, label="Standard Normal", mean=0.0, sigma=1.0)
self.register_task(SampleGaussian, label="Wide Gaussian", mean=0.0, sigma=10.0)
```

Both appear in the **Tasks** menu asking only for `seconds`.

### Tasks that are already included

A few tasks come with `pyacquisition`. `NewFile`, `WaitFor` and `WaitUntil` are registered for you. Others, such as `SweepMagneticField`, are imported from `pyacquisition.tasks` and registered like your own. See the [list of tasks](../tasks/overview.md).

## Things to watch for

- **Do not name an input after something a task already has.** Names such as `start`, `name`, `description`, `parameters`, `run`, `setup`, `teardown`, `pause`, `resume` and `abort` are taken, and so is `label`, which `register_task` uses. An input called `start`, for example, fails with a confusing error about *"non-default argument follows default argument"*. Choose something more specific, such as `start_value`.
- **Defaults apply in code, not in the form.** When you create a task yourself (for example [as part of another task](composing_tasks.md)), its defaults are used. The interface's form and the API currently ask for every input.
- **Errors do not crash the experiment.** If `run()` raises an error, `teardown()` runs and the task manager moves on to the next task. The error message is printed in the terminal where you started the experiment, not in the **Logs** window, so look there when a task ends sooner than you expect.

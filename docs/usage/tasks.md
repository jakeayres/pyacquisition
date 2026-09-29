# Writing Tasks

!!! note "These pages use a different example"
    The three pages on tasks build one small experiment out of a random number generator, which is written on [Writing your own instrument](custom_instruments.md#a-software-instrument).

A **task** is a procedure that you want to run on your experiment: record data under one condition, wait an hour, start a new file, ramp a temperature. Tasks are run from a queue, one at a time, and can be paused or aborted while they run. You can queue them from the interface, and you can build bigger tasks [out of smaller ones](composing_tasks.md).

## Your first task

Here is a task that makes the random number generator draw from a Gaussian distribution for a number of seconds. Add it to `my_experiment.py`:

```python title="my_experiment.py" linenums="1" hl_lines="1 3 8-23 38"
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

    async def run(self, experiment): # (4)!
        rng = experiment.instruments["rng"] # (5)!
        rng.use_gaussian(self.mean, self.sigma)
        self.log(f"Sampling a Gaussian with mean {self.mean} and sigma {self.sigma}") # (6)!
        await self.sleep(self.seconds) # (7)!

    async def teardown(self, experiment): # (8)!
        experiment.instruments["rng"].use_gaussian(0.0, 1.0)


class MyExperiment(Experiment):
    data_path = "my_data"

    def setup(self):
        clock = Clock("clock")
        rng = RandomNumberGenerator("rng")
        self.add_instrument(clock)
        self.add_instrument(rng)

        self.add_measurement(Measurement("time", clock.time))
        self.add_measurement(Measurement("random", rng.random_number))

        self.register_task(SampleGaussian, label="Sample Gaussian") # (9)!


if __name__ == "__main__":
    MyExperiment().run()
```

1. **Every task class needs the `@dataclass` decorator.** It turns the annotated attributes below into the task's inputs. Without it the task registers with no inputs and fails when it runs.
2. The first line of the docstring is shown in the interface as the description of the task. See [what the queue shows](#what-the-queue-shows) to write something more specific.
3. **Inputs** are annotated attributes. Ones without a default value are required. Use `int`, `float`, `str` or `bool`.
4. `run()` is where the work happens. It is an ordinary `async` method. Everything you need to know about it is [explained below](#how-run-works).
5. `experiment` is your experiment. `experiment.instruments` is how a task reaches the instruments it controls.
6. `self.log(...)` writes a message to the log, labelled with the name of the task.
7. Wait with `await self.sleep(...)`. It waits without blocking anything else, and it is a place where the task can be paused and aborted. Never use `time.sleep()` in a task, which would freeze the entire experiment while it waits.
8. `teardown()` always runs when the task ends, including when it was aborted or hit an error. Use it to leave your instruments in a safe state. Here, the generator goes back to its default distribution.
9. Register the task, passing the class itself (not an instance: no brackets). It can now be queued from the interface. `label` sets the name it is listed by.

Run the experiment, open the **Queue** tab, press **Add task** and pick **Sample Gaussian**. Its form starts at the defaults: set `mean` 5, `sigma` 2 and `seconds` 10, and press **Add to queue**. The task joins the queue and starts. Watch `random` on the plot settle around 5 for ten seconds, then return to a spread around 0 when the task ends. [Running tasks](running_tasks.md) covers what you can do with the queue.

## What the queue shows

The **Queue** tab shows each task's `description` and `parameters`. By default, the description is the first line of the task's docstring, and the parameters are its inputs. To show something more useful, override them as properties:

```python
@property
def description(self):
    return f"Sample a Gaussian distribution for {self.seconds} s"

@property
def parameters(self):
    return {"mean": self.mean, "sigma": self.sigma}
```

The queue is refreshed about once a second, and `parameters` is read each time, so it can return values that change while the task runs, such as the latest reading.

### Showing progress

A task can say how far along it is with `self.set_progress(...)`, as it goes. The interface shows it on the running task as a bar, with how long the task has run and how long is left, and in its top bar.

```python
async def run(self, experiment):
    for i, kelvin in enumerate(self.points):
        self.set_progress(i, of=len(self.points), note=f"Going to {kelvin} K")
        await self.run_subtask(SetTemperature(kelvin))
    self.set_progress(len(self.points), of=len(self.points))
```

- `set_progress(0.4)` is a fraction from 0 to 1, and `set_progress(3, of=10)` counts steps, shown as "3 of 10".
- `note=` says what it is doing now.
- `remaining=` gives the seconds left, where the task knows them (a wait does). Otherwise the interface estimates them from the time taken so far.
- The time a task spends paused does not count towards how long it has run.
- A subtask's progress is shown under the task running it.

The included waits, `RampTemperature` and the magnet sweeps already report their progress.

## How `run()` works

`run()` is an `async def` method. You do not need to understand asynchronous programming to write one, but a few rules matter.

**Wait with the task's own waits.** They wait without blocking the rest of the experiment (the measurements, the interface), and each one is a place where the task can be **paused and aborted**:

| Call | What it does |
|---|---|
| `await self.sleep(seconds)` | Waits. The time does not pass while the task is paused, so `sleep(300)` is five minutes of running time. |
| `await self.wait_until(condition)` | Waits until `condition()` returns true, checking every `poll` seconds (1 by default). Give it a `timeout` to stop waiting eventually. It raises `TimeoutError` if it runs out. For example `await self.wait_until(lambda: psu.get_sweep_status() == REST)`. |
| `await self.checkpoint()` | A place where the task can be paused or aborted, for a loop of your own that calls none of the others. |
| `await self.run_subtask(...)` | Runs another task. See [composing tasks](composing_tasks.md). |
| `self.log("...")` | Writes a message to the log, labelled with the task's name. It is not a wait, so it needs no `await`. |
| `self.expect(actual, wanted, "What")` | Checks a value, and raises an error if it is not the one you wanted. See [checking what you set](#checking-what-you-set). |
| `self.set_progress(done, of=None)` | Says how far along the task is, for the interface to show. It is not a wait. See [showing progress](#showing-progress). |

These work wherever you call them, however deep in your own helper methods, so you can split a long task into `async def` methods of its own and `await` them.

**Aborting is immediate.** An abort stops the task wherever it is waiting, even in the middle of a long `sleep`, and then runs `teardown()`. It does not wait for the next step.

**Pausing stops the task, not your hardware.** A paused task stops at its next wait, and no code after it runs until it is resumed. Whatever the instruments were doing carries on. If that matters, say what a pause should do in [`on_pause()` and `on_resume()`](#pausing-hardware-on_pause-and-on_resume).

**Everything else is ordinary Python.** Loops, conditions, calling instrument methods, and calculations all work as usual. Instrument calls are normal (not `async`) function calls. The code between two waits runs without interruption, and nothing else in the experiment runs meanwhile, so a series of instrument commands is never broken up by another task, a measurement or a pause. The price is that a call that takes a long time to return holds everything up, so keep instrument calls short.

!!! note "Older tasks that `yield`"
    `run()` can also be an *async generator* that `yield`s a message, or `None`, at each place it can be paused. Tasks written that way still work, and each `yield` is a wait. New tasks do not need it.

## Pausing hardware: `on_pause()` and `on_resume()`

By default, pausing a task only stops it from doing anything more. A ramp that the instrument is carrying out on its own, such as a magnet sweeping to a field, carries on. If pausing should do something to your hardware, write two methods:

```python
@dataclass
class RampMagnet(Task):
    """Sweep the magnet to a field."""

    magnet: str
    field: float

    async def run(self, experiment):
        psu = experiment.instruments[self.magnet]
        psu.set_target_field(self.field)
        psu.to_setpoint()
        await self.wait_until(lambda: psu.get_sweep_status() == REST)

    def on_pause(self, experiment):
        experiment.instruments[self.magnet].hold() # (1)!

    def on_resume(self, experiment):
        psu = experiment.instruments[self.magnet]
        self.expect(psu.get_system_status(), NORMAL, "System status") # (2)!
        psu.to_setpoint()

    async def teardown(self, experiment):
        experiment.instruments[self.magnet].hold() # (3)!
```

1. Pausing puts the magnet on hold.
2. Resuming first checks that the system is still normal, because a magnet that quenched while it was held must not be sent on its way. If the check raises an error, the task does not carry on: it fails, and `teardown()` runs.
3. However the task ends, the magnet is left holding, not sweeping.

How they behave:

- **They are called at once**, when you press **Pause** or **Resume**, and not when the task next reaches a wait. They are ordinary methods, like the instrument calls in them.
- **`on_resume()` finishes before the task carries on.** A `wait_until` is never checked while the task is paused, so a magnet that reads as at rest because it is held is not taken to have arrived.
- **Once for each pause**, and only while `run()` is in progress. A task that is paused before it starts, or while it is in `setup()`, waits before it runs, and has no hooks called. Aborting a paused task does not call `on_resume()`. It calls `teardown()`, which is where a safe state belongs.
- **Subtasks have their own.** Pausing a task pauses the subtask that is running, and calls that subtask's `on_pause()` first, then its own. So put the hooks on the small task that owns the hardware, and a larger task built from it needs none.
- **An error in a hook fails the task.**

## `setup()` and `teardown()`

Tasks have two optional hooks in addition to `run()`:

| Method | Runs | Use it to |
|---|---|---|
| `setup(self, experiment)` | Before `run()` | Prepare the instruments |
| `teardown(self, experiment)` | After `run()`, **always** | Return the instruments to a safe state |

Both are `async def` methods, but ordinary code works inside them. `teardown()` runs when the task finishes normally, when it is aborted, and when it raises an error. If `setup()` raises an error, `run()` is skipped and `teardown()` still runs.

**`teardown()` is never paused or aborted.** Pressing **Pause** or **Abort** a second time while it runs does not interrupt it, and `self.sleep()` and the other waits in it wait as normal. It always gets to finish, so it is safe to use it to put an instrument into a safe state.

## Checking what you set

A task that controls hardware should not assume that a command worked. `self.expect()` compares a value with the one you wanted, and raises an error if they differ. A task that fails an `expect` stops at that point, before it does anything further:

```python
psu.set_field_sweep_rate(self.ramp_rate)
await self.sleep(1)
self.expect(psu.get_field_sweep_rate(), self.ramp_rate, "Ramp rate")

self.expect(psu.get_activity_status(), ActivityStatus.HOLD, "Activity")
self.expect(reading, 1.0, "Field", tolerance=0.001)
```

By default the values must be equal. Give a `tolerance` to accept numbers that are close. A check that passes is written to the log (`Ramp rate: 0.2 OK`), and one that fails raises a `ValueError` naming both values (`Activity: expected HOLD, got TO_SETPOINT`). Enum members are shown by name.

## How a task ends

A task ends in one of three ways, and its `teardown()` runs in all of them:

| Outcome | When |
|---|---|
| `completed` | `run()` finished. |
| `aborted` | You aborted it, or the experiment shut down. |
| `failed` | `run()`, `setup()`, `teardown()`, `on_pause()` or `on_resume()` raised an error. |

A failure does not crash the experiment. An alert says which task failed and why, and the error appears in the **Logs** tab (`[SampleGaussian] Task failed: ValueError: ...`), with the traceback in the terminal and the log file. **The task manager then pauses**, as it does after an abort, so the tasks queued behind a task that failed, which may rely on it having worked, do not run on their own. Press **Resume** to carry on with them, or clear the queue.

Code can read the outcome from `task.outcome` (`None` until it has ended) and the error from `task.failure`. The result of the last task on each task manager is also in `/managers/state`, under `last_result`.

## Registering tasks

Tasks must be registered in `setup()` to be queued from the interface:

```python
self.register_task(SampleGaussian, label="Sample Gaussian")
```

| Argument | Effect |
|---|---|
| The class | Required. Pass the class, not an instance. |
| `label` | The name it is listed by, and its API address (`/tasks/sample_gaussian`). Without it the class name is used, and the address is the class name in lower case, run together: `SampleGaussian` and `/tasks/samplegaussian`. |
| Other keywords | Fix an input to a value. The task then appears with that input hidden. |

Fixing inputs lets you offer ready-made variants of a general task:

```python
self.register_task(SampleGaussian, label="Standard Normal", mean=0.0, sigma=1.0)
self.register_task(SampleGaussian, label="Wide Gaussian", mean=0.0, sigma=10.0)
```

Both are listed in **Add task**, asking only for `seconds`.

### Tasks that are already included

A few tasks come with `pyacquisition`. `NewFile`, `WaitFor` and `WaitUntil` are always registered for you, and so are `PauseMeasurements`, `ResumeMeasurements` and `SetMeasurementPeriod`, to pause the measurements or change how often they are taken at a point in a queue ([Measurements](../reference/tasks/measurements.md)).

**Tasks for an instrument register themselves when it is there.** `RampTemperature` is for the Lakeshore 340 and 350, and `SweepMagneticField` is for the Mercury IPS. Add one of those instruments, in `setup()` or in a [TOML file](../reference/config_file.md), and its task can be queued (as **Ramp Temperature** and **Sweep Magnetic Field**) with nothing else to write. They are registered once `setup()` has finished, so it does not matter in which order you add things.

- **The instrument's id is filled in for you** when there is exactly one such instrument, so the form does not ask for it. With two, such as a Lakeshore 340 and a 350, the form asks which, from a list of them.
- **A task that you registered yourself is left as you registered it.** Do that to choose the label, to fix some of its inputs, or to limit it to a task manager.
- **A task whose instrument is absent is not registered.**

To turn it off, set `auto_tasks` to `False`, and register whichever of these tasks you want with `register_task`:

```python
class MyExperiment(Experiment):
    auto_tasks = False

    def setup(self):
        ...
        self.register_task(RampTemperature, label="Ramp", lakeshore="cryostat")
```

In a TOML file, it is `auto_tasks = false` under `[experiment]`. See the [list of tasks](../reference/tasks/overview.md) for which tasks are registered by themselves. Tasks that are only building blocks, such as `RampMagnet`, and ones that need more than an instrument, such as `PID`, are imported from `pyacquisition.tasks` and registered like your own.

**A task input that is a choice** (which output to ramp, say) is asked for as text in the form and the API: `OUTPUT_1`, or the label `Output 1`, in any case. A name that matches nothing is refused, and the message lists the ones that do.

## Things to watch for

- **Do not name an input after something a task already has.** Names such as `start`, `name`, `description`, `parameters`, `run`, `setup`, `teardown`, `pause`, `resume`, `abort`, `on_pause`, `on_resume`, `log`, `sleep`, `wait_until`, `checkpoint`, `expect`, `set_progress`, `progress`, `elapsed`, `timing`, `outcome`, `failure`, `paused` and `applies_to` are taken, and so is `label`, which `register_task` uses. An input called `start`, for example, fails with a confusing error about *"non-default argument follows default argument"*. Choose something more specific, such as `start_value`.
- **Defaults apply in code, not in the form.** When you create a task yourself (for example [as part of another task](composing_tasks.md)), its defaults are used. The interface's form and the API currently ask for every input.
- **Wait with `self.sleep()`, not `asyncio.sleep()`.** A task that waits with `asyncio.sleep()` can still be aborted, but it cannot be paused until its wait is over, and the time keeps passing while it is paused.
- **Catch `Exception`, never everything.** Aborting a task raises `asyncio.CancelledError` inside it. `except Exception` does not catch that, as it should not, but a bare `except:` does, and it stops you being able to abort.

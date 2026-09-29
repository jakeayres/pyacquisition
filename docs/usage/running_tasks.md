# Running Tasks

Once tasks are [registered](tasks.md#registering-tasks), you run them by adding them to the **queue**. The task manager takes tasks from the queue one at a time, in the order they were added, and runs each to completion before starting the next.

## Queueing a task

1. Open the **Queue** tab and press **Add task** (with several task managers, on the one it should run on).
2. Pick your task. Search to narrow the list, and use the arrow keys and ++enter++ to go to its form.
3. Fill in its inputs. Each starts at its default from your code, if it has one, and an input marked with a star must be given.
4. Press **Add to queue**. The window stays open, so you can add several tasks in turn, and **Done** closes it.

++ctrl+k++ does the same from anywhere: it searches every task on every task manager, and queues the one you pick. Its inputs can be typed after its name, as in `wait 0 5`, to queue it with ++enter++ without the form.

The task joins the queue, and starts as soon as the task manager is free. An instrument's query or command can be queued the same way, from the **Instruments** tab or ++ctrl+k++ ([Using an instrument from the interface](instruments.md#using-an-instrument-from-the-interface)): it shows in the queue as the call, such as `lakeshore.set_setpoint(output_channel=OUTPUT_1, setpoint=300)`. You can queue several tasks, including several copies of the same one with different inputs, and then leave them to run.

## The Queue tab

The **Queue** tab shows, for each task manager:

- **The header**: its state (**Running**, **Paused**, **Aborting…** or **Idle**), **Add task**, and **Pause** (which becomes **Resume** while it is paused).
- **The running task**, in a card: its `description` and `parameters` (if you [wrote them](tasks.md#your-first-task)), how long it has been running, how far along it is and how long is left, if it [says](tasks.md#showing-progress), the subtasks it is running, and **Abort**. The card is green while the task runs, amber while the task manager is paused, and red while the task is being aborted. Its copy button queues the same task again. The name of the running task is in the top bar too, whichever tab is open.
- **The queue**: the tasks waiting behind it, in order, with their inputs. The running task is not repeated here. Each waiting task has buttons to move it one place **up** (so that it runs sooner) or **down**, to copy it, and to remove it (**×**). You can also drag it by the handle at its left to any place. It is always the task you clicked that is moved or removed, even if the queue has moved on since you last looked, for example because the task in front of it has just started. The first task cannot move up, because the place in front of it belongs to the task that is running, and the last cannot move down, so those arrows are greyed out.
- **Save…**, **Load…** and **Clear queue**: [sequences](#saving-a-queue-as-a-sequence), and emptying the queue (after asking). Clearing does not stop the task that is running.

Everything a task logs with `self.log(...)` appears in the **Logs** tab, labelled with the task's name, so you can follow its progress there. So does a task that fails, with the reason, and an alert says so as well.

## Pause, resume and abort

The buttons in the **Queue** tab control what is running:

| Button | What it does |
|---|---|
| **Pause** | The running task stops at its next wait and holds there. If it has an [`on_pause()`](tasks.md#pausing-hardware-on_pause-and-on_resume), that is called at once, so a task that controls a magnet can put it on hold. Otherwise the instruments are left as they are. No new task is started. |
| **Resume** | The task's `on_resume()` is called if it has one, and then the task carries on from where it stopped, and the queue continues. |
| **Abort** | After asking you to confirm, the running task stops at once, wherever it is waiting, and its `teardown()` runs, leaving the instruments in the safe state you defined. The task manager then **pauses**, so the next task does not start until you press **Resume**. |

A task pauses at its waits (`self.sleep()`, `self.wait_until()` and so on: see [How `run()` works](tasks.md#how-run-works)), so a pause takes effect when the task next reaches one. An abort does not wait for one.

!!! note "Abort pauses the whole queue"
    Aborting deliberately does not go straight on to the next task. Nothing else runs until you decide, by pressing **Resume**, or by clearing the queue first with **Clear queue**.

!!! note "An abort stops the task at once, and then its `teardown()` runs"
    The task is stopped wherever it is waiting, and then its `teardown()` runs, which is never interrupted, even by a second press of **Abort**. A `teardown()` that takes a while, for example one that waits for an instrument to settle, therefore keeps the card red, and the task manager **Aborting…**, until it has finished.

!!! note "A task that fails pauses the queue too"
    If a task raises an error, an alert says so, the error is in the **Logs** tab, its `teardown()` runs, and the task manager **pauses**, as it does after an abort. The tasks behind it may rely on it having worked, so they do not run on their own. Press **Resume** to carry on with them, or **Clear queue**. How the last task ended (`completed`, `failed` or `aborted`, and the error) is in `/managers/state`, under `last_result`.

## Several task managers

One task manager runs its tasks one after another. For work that has to carry on *while* the queue does something else, such as a control loop that runs for the whole experiment, add another task manager. Each one has its own queue, and they all run at the same time. Each is paused, resumed and aborted on its own.

```python
def setup(self):
    control = self.add_task_manager("control") # (1)!
    self.register_task(Calibrate) # (2)!
    self.register_task(HoldTemperature, manager="control") # (3)!
    control.add_task(LogPressure()) # (4)!
```

1. The name may contain letters, numbers, `_` and `-`. The task manager you have used so far is called `"main"`, and it is always there. Add task managers in `setup()`: like instruments, they cannot be added once the experiment is running.
2. **A registered task can be queued on any task manager.** This includes the standard tasks (`NewFile`, `WaitFor` and so on), and task managers that you add after registering it.
3. To limit a task to one task manager, name it with `manager=`. Give a list of names to allow several: `manager=["control", "other"]`.
4. You can also queue a task directly. It starts as soon as the experiment does, which is how you start something that should always be running. `self.task_managers["control"]` gives you a task manager by name.

A task that never finishes holds up only the queue it is in, and it is stopped, running its `teardown()`, when the experiment shuts down.

!!! warning "Anything queued behind a task that never finishes waits for ever"
    A queue runs one task at a time. If an endless task, such as a [PID](../reference/tasks/pid.md), is running on a task manager, the tasks you queue on that same task manager wait behind it until it is stopped. Give an endless task a task manager of its own (`self.add_task_manager("pid")`), and use the others for tasks that finish.
 The task managers share one thread, so [the same rules apply as when tasks run together](composing_tasks.md#running-tasks-at-the-same-time): every loop needs an `await`, and a task that blocks holds up all the others. Nothing stops two task managers from changing the same instrument setting, so decide which one owns each.

Use one task manager for a set of tasks that must run *one after another*. To run things at the same time *within* one task, see [Running tasks at the same time](composing_tasks.md#running-tasks-at-the-same-time).

| Address | Does |
|---|---|
| `/task_manager/...` and `/tasks/<label>` | The `"main"` task manager, as described on this page. |
| `/managers/<name>/pause`, `/resume`, `/abort`, `/status`, `/current_task`, `/task_list`, `/remove_task`, `/clear_tasks` | The same controls for the task manager called `<name>`. |
| `/managers/<name>/tasks/<label>` | Queue a registered task on that task manager. |
| `/managers` | The names of all the task managers. |
| `/managers/state` | The status, running task and queue of every task manager, in one call. The interface polls this. |

### In the interface

With more than one task manager, the **Queue** tab has a section for each, one under another, with its own header, state, running task, queue and buttons, so you can see at a glance that a control loop is still going. **Add task** on a section lists only the tasks that can be queued on that task manager. The top bar names the first task that is running, with a count of any others (**+1**), and ++ctrl+k++ offers each task once for every task manager it can be queued on.

## Running tasks from a script

The interface is only one client of the [API](../reference/web_api.md). You can queue and manage tasks from any Python script or notebook with `requests`. Every input is passed as a query parameter. An input with a default can be left out:

```python
import requests

base = "http://localhost:8000"

requests.get(
    f"{base}/tasks/sample_gaussian",
    params={"mean": 5, "sigma": 2, "seconds": 10},
)
requests.get(
    f"{base}/tasks/compare_distributions",
    params={"seconds": 10},
) # (1)!
```

1. The address of a task is `/tasks/` followed by its `label` in lower case, with spaces replaced by underscores. Look at [http://localhost:8000/docs](http://localhost:8000/docs) to see the exact address and inputs of every task.

The task manager has endpoints of its own:

| Address | Does |
|---|---|
| `/task_manager/pause`, `/task_manager/resume` | Pause and resume. |
| `/task_manager/abort` | Abort the running task. |
| `/task_manager/current_task` | The name of the running task, or `None`. |
| `/task_manager/task_list` | The tasks waiting in the queue. |
| `/task_manager/status` | `Running` or `Paused`. |

To wait until everything you have queued has finished:

```python
import time

def wait_until_idle():
    time.sleep(1) # give the task manager a moment to pick up the first task
    while (
        requests.get(f"{base}/task_manager/current_task").json()["data"] is not None
        or requests.get(f"{base}/task_manager/task_list").json()["data"]
    ):
        time.sleep(1)
```

To remove one waiting task, `/task_manager/remove_task?N=` takes its position, and `/task_manager/remove_queued_task?task_id=` takes its id instead, which cannot pick the wrong task if the queue has moved on. Every task in the queue, and the running task, has an `id` in `/managers/state`. To move one, `/task_manager/move_queued_task?task_id=...&direction=up` (or `down`) moves it one place, and answers `{"moved": false}` if it cannot go that way. `/task_manager/place_queued_task?task_id=...&index=0` puts it at a place (0 is the front), and `/task_manager/duplicate_queued_task?task_id=...` queues a copy straight after it (or at the front, for the running task). (These are what the buttons in the queue use. They are not listed at [http://localhost:8000/docs](http://localhost:8000/docs).) Other task managers have them at `/managers/<name>/...`.

That makes it possible to run a whole series of experiments unattended, from a script that queues tasks, waits, analyses the data files, and decides what to queue next.

## Saving a queue as a sequence

A queue you will want again, such as a cooldown or an overnight sweep, can be saved as a **sequence** and loaded later, in the same run or the next. The **Queue** tab has **Save…** and **Load…** beside each queue, and the API has them too:

| Address | Does |
|---|---|
| `/sequences` | The sequences saved, each with its name, when it was saved and its tasks' names. |
| `/sequences/save?name=cooldown` | Saves the main queue, starting with the running task (`include_running=false` leaves it out). `manager=` saves another task manager's. A name that is taken is refused unless `overwrite=true`. |
| `/sequences/load?name=cooldown` | Queues the sequence's tasks after those already queued. `manager=` loads onto another task manager. |
| `/sequences/delete?name=cooldown` | Deletes it. |

Sequences are JSON files in a `sequences` folder under the experiment's `root_path`, one for each, which can be copied between experiments or edited by hand. Each task is saved as it was queued, by its address and the inputs it was given, so:

- **Only tasks queued from the interface or the API are saved.** Tasks queued in code, such as in `setup()`, are left out, and saving says which.
- **Loading is all or nothing.** If a task can't be queued (it isn't registered in this experiment, or an input no longer fits), nothing is queued, and the reason is given for each such task.
- **An input a task has gained since the sequence was saved takes its default.**

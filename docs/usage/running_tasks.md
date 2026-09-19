# Running Tasks

Once tasks are [registered](tasks.md#registering-tasks), you run them by adding them to the **queue**. The task manager takes tasks from the queue one at a time, in the order they were added, and runs each to completion before starting the next.

## Queueing a task

1. Open the **Tasks** menu and choose your task.
2. Fill in **every** input. The inputs start at zero or empty, and the defaults from your code are not filled in for you.
3. Press **Send Request**.

The task joins the queue, and starts as soon as the task manager is free. You can queue several tasks, including several copies of the same one with different inputs, and then leave them to run.

## The Task Queue window

The **Task Queue** window shows:

- **The header**: the name of the task that is running now, and a badge for the state of the task manager: **RUNNING** (green), **PAUSED** (amber), **ABORTING** (red) or **IDLE** (grey).
- **Queue**: the tasks waiting behind it, in order, with their `description` and `parameters` (if you [wrote them](tasks.md#your-first-task)). The running task is not repeated here. Each waiting task has a **Remove** button, which takes that task out of the queue straight away. It is the task you clicked that is removed, even if the queue has moved on since you last looked, for example because the task in front of it has just started. The two arrows beside it move that task one place **up**, so that it runs sooner, or **down**. The first task in the queue cannot move up, because the place in front of it belongs to the task that is running, and the last cannot move down, so those arrows are greyed out. Like **Remove**, an arrow moves the task you clicked, wherever it now is.

Each step that a task yields appears in the **Logs** window, labelled with the task's name, so you can follow its progress there.

## Pause, resume and abort

Use the **Task Manager** menu to control what is running. With [several task managers](#several-task-managers), the **Pause** and **Abort** buttons on each one's card do the same, and aborting asks you to confirm first.

| Menu item | What it does |
|---|---|
| **Pause** | The running task stops at its next step and holds there, with the instruments left as they are. No new task is started. |
| **Resume** | The running task carries on from where it stopped, and the queue continues. |
| **Abort Current Task** | The running task stops at its next step, and its `teardown()` runs, leaving the instruments in the safe state you defined. The task manager then **pauses**, so the next task does not start until you press **Resume**. |
| **Remove Task** | Removes one task from the queue. Give its position `N`: `0` is the next task to run. The **Remove** buttons in the **Task Queue** window are safer, because the queue can move up between you looking at a position and the request arriving. |
| **Clear All Tasks** | Empties the queue. It does not stop the task that is running. |

A task can only pause or stop *between steps*, at its `yield` statements (see [How `run()` works](tasks.md#how-run-works)). If a task seems slow to respond, that is because it is in the middle of a step.

!!! note "Abort pauses the whole queue"
    Aborting deliberately does not go straight on to the next task. Nothing else runs until you decide, by pressing **Resume**, or by clearing the queue first with **Clear All Tasks**.

!!! note "An abort takes effect at the task's next step"
    The task is told to stop at once, but it only stops when it reaches its next `yield`, and then runs its `teardown()`. A task that takes a long time over each step therefore takes that long to stop. Until it has, its card is red and reads **ABORTING**.

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
    A queue runs one task at a time. If an endless task, such as a [PID](../tasks/pid.md), is running on a task manager, the tasks you queue on that same task manager wait behind it until it is stopped. Give an endless task a task manager of its own (`self.add_task_manager("pid")`), and use the others for tasks that finish.
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

With more than one task manager, the interface adds them alongside the main one:

- **The Task Queue window** has a section for each task manager. The header shows its name, the task that is running, and a badge for its state (**RUNNING**, **PAUSED**, **ABORTING** or **IDLE**) in a matching colour, so you can see at a glance that a control loop is still going. Below it, the task that is running is shown in full in a highlighted card, with its description and parameters, in the same way as in the queue. The card is **green** while the task runs, **amber** when it is paused, **red** while it is being aborted, and grey when nothing is running. Its two buttons, at the top right, are one click away from the **Task Manager** menu:
    - **Pause** pauses that task manager, and becomes **Resume** when it is paused. It works when nothing is running too, so a paused queue can always be resumed from here.
    - **Abort** stops the task that is running, after asking you to confirm. It is greyed out when nothing is running, and while an abort is already under way.

    The queue is underneath. Click a header to collapse its section, and click it again to expand it (the arrow at its left shows which). The header stays, so its state is still visible.
- **The Task Manager and Tasks menus** have a submenu for each task manager. The **Tasks** submenu of a task manager lists the tasks that can be queued on it, so choosing a task there queues it on that task manager. A task manager that no task can be queued on is left out.
- **Windows are titled with the task manager**, for example **control: Pause**, so that the same action on two task managers can be told apart.

With only the main task manager, the window and menus are exactly as described on the rest of this page.

## Running tasks from a script

The interface is only one client of the [API](running.md#the-api). You can queue and manage tasks from any Python script or notebook with `requests`. Every input is passed as a query parameter, and every input must be given:

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

To remove one waiting task, `/task_manager/remove_task?N=` takes its position, and `/task_manager/remove_queued_task?task_id=` takes its id instead, which cannot pick the wrong task if the queue has moved on. Every task in the queue, and the running task, has an `id` in `/managers/state`. To move one, `/task_manager/move_queued_task?task_id=...&direction=up` (or `down`) moves it one place, and answers `{"moved": false}` if it cannot go that way. (`remove_queued_task` and `move_queued_task` are what the buttons in the queue use. They are not listed at [http://localhost:8000/docs](http://localhost:8000/docs), so that they do not appear as entries in the **Task Manager** menu.) Other task managers have them at `/managers/<name>/...`.

That makes it possible to run a whole series of experiments unattended, from a script that queues tasks, waits, analyses the data files, and decides what to queue next.

# Running Tasks

Once tasks are [registered](tasks.md#registering-tasks), you run them by adding them to the **queue**. The task manager takes tasks from the queue one at a time, in the order they were added, and runs each to completion before starting the next.

## Queueing a task

1. Open the **Tasks** menu and choose your task.
2. Fill in **every** input. The inputs start at zero or empty, and the defaults from your code are not filled in for you.
3. Press **Send Request**.

The task joins the queue, and starts as soon as the task manager is free. You can queue several tasks, including several copies of the same one with different inputs, and then leave them to run.

## The Task Queue window

The **Task Queue** window shows:

- **Running Status**: `Running` or `Paused`.
- **Current Task**: the task that is running now.
- **Queue**: the tasks waiting behind it, in order, with their `description` and `parameters` (if you [wrote them](tasks.md#your-first-task)). The running task is not repeated here.

Each step that a task yields appears in the **Logs** window, labelled with the task's name, so you can follow its progress there.

## Pause, resume and abort

Use the **Task Manager** menu to control what is running.

| Menu item | What it does |
|---|---|
| **Pause** | The running task stops at its next step and holds there, with the instruments left as they are. No new task is started. |
| **Resume** | The running task carries on from where it stopped, and the queue continues. |
| **Abort Current Task** | The running task stops at its next step, and its `teardown()` runs, leaving the instruments in the safe state you defined. The task manager then **pauses**, so the next task does not start until you press **Resume**. |
| **Remove Task** | Removes one task from the queue. Give its position `N`: `0` is the next task to run. |
| **Clear All Tasks** | Empties the queue. It does not stop the task that is running. |

A task can only pause or stop *between steps*, at its `yield` statements (see [How `run()` works](tasks.md#how-run-works)). If a task seems slow to respond, that is because it is in the middle of a step.

!!! note "Abort pauses the whole queue"
    Aborting deliberately does not go straight on to the next task. Nothing else runs until you decide, by pressing **Resume**, or by clearing the queue first with **Clear All Tasks**.

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

That makes it possible to run a whole series of experiments unattended, from a script that queues tasks, waits, analyses the data files, and decides what to queue next.

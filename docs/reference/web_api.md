# Web API

The endpoints a script or notebook uses to read, command and queue a running experiment. The interface uses the same ones. [Drive an experiment from a script](../usage/api_script.md) uses them, and [Queue, pause and save tasks](../usage/queue.md) shows the queue they control.

The experiment serves them at its own address, `http://localhost:8000` unless [`api_server_port`](experiment_options.md) says otherwise. Every endpoint is a `GET`, with its inputs as query parameters:

```python
import requests

base = "http://localhost:8000"
requests.get(f"{base}/clock/time").json()
# {'status': 200, 'data': 0.523862361907959}
requests.get(f"{base}/tasks/waitfor", params={"seconds": 2}).json()
# {'status': 200, 'message': 'WaitFor added'}
```

Most answer `{"status": 200, "data": ...}`. The rack's, and a few others, answer `{"status": "success", ...}`. A running experiment lists every endpoint, with its inputs, at `/docs`, where each can be tried.

An endpoint that can't do what it was asked answers with an error status, and a `detail` that says why. `requests`' `raise_for_status()` turns each into an exception.

| Status | When | Answer |
|---|---|---|
| 404 | There is no such endpoint: a name mistyped, say. | `{"detail": "Not Found"}` |
| 422 | An input is missing, misnamed, or can't be read as its type. | `{"detail": [{"type": "missing", "loc": ["query", "frequency"], "msg": "Field required", ...}]}` |
| 500 | The query or command itself raised an error. | `{"detail": "There is no folder called 'nowhere'."}`: the error's message, or its kind if it has none |

## Instruments

| Endpoint | Does | Answers, for example |
|---|---|---|
| `/<instrument>/<method>` | Calls a query or command, with its arguments as parameters: `/lockin/set_frequency?frequency=1000`. A choice is given by its label, exactly as the interface shows it. | `{"status": 200, "data": 1000.0}` |
| `/<instrument>/queries/` | The instrument's queries. | `{"status": 200, "data": ["list_timers", "time", ...]}` |
| `/<instrument>/commands/` | The instrument's commands. | |
| `/rack/list_instruments` | Each instrument's name, with its driver's. | `{"status": "success", "instruments": {"lockin": "SR_830", ...}}` |

## Measurements

| Endpoint | Does | Answers, for example |
|---|---|---|
| `/rack/list_measurements` | The measurements. | `{"status": "success", "measurements": {"time": "time", ...}}` |
| `/rack/period/get/` | The polling period, in seconds. | `{"status": "success", "period": 0.2}` |
| `/rack/period/set/?period=0.5` | Sets the polling period. | |
| `/rack/pause/`, `/rack/resume/` | Pauses and resumes measuring. | |
| `/rack/state` | Whether measuring is paused, the period set, and the time the latest loops took on average. | `{"status": "success", "paused": false, "period": 0.2, "loop_time": 0.2032}` |
| `/history` | The rows kept in memory for the plots. | |

## Data files

| Endpoint | Does | Answers, for example |
|---|---|---|
| `/scribe/current_file` | The file being written. | `{"status": 200, "data": "02.00 start.data"}` |
| `/scribe/current_directory` | Its folder. | |
| `/scribe/next_file?title=run 1` | Starts a new file now. `next_block=true` starts a new block. | |
| `/scribe/state` | The file, its folder, and the names the next file would take. | |

## Tasks and the queue

A task registered with the experiment is queued at `/tasks/<task>`, where `<task>` is its label in lower case with spaces as underscores, and its inputs are parameters: `/tasks/waitfor?seconds=2`.

| Endpoint | Does | Answers, for example |
|---|---|---|
| `/tasks/<task>` | Queues the task. | `{"status": 200, "message": "WaitFor added"}` |
| `/task_manager/current_task` | The running task's name, or `null`. | `{"status": 200, "data": "WaitFor"}` |
| `/task_manager/task_list` | The tasks waiting. | `{"status": 200, "data": []}` |
| `/task_manager/status` | `Running` or `Paused`. | `{"status": 200, "data": "Running"}` |
| `/task_manager/pause`, `/task_manager/resume` | Pauses and resumes the queue. | |
| `/task_manager/abort` | Aborts the running task. | |
| `/task_manager/clear_tasks` | Removes every waiting task. | |
| `/task_manager/remove_task?N=0` | Removes the waiting task at a place, counting from 0. | |
| `/task_manager/remove_queued_task?task_id=...` | Removes a waiting task by its id, which can't pick the wrong one if the queue has moved on. | |
| `/task_manager/move_queued_task?task_id=...&direction=up` | Moves a waiting task one place, `up` or `down`. | `{"moved": false}` if it can't |
| `/task_manager/place_queued_task?task_id=...&index=0` | Puts a waiting task at a place, 0 being the front. | |
| `/task_manager/duplicate_queued_task?task_id=...` | Queues a copy straight after it, or at the front for the running task. | |
| `/task_manager/call/<instrument>/<method>` | Queues a query or command, to run in its turn. | |
| `/managers` | The task managers' names. | `{"status": 200, "data": ["main"]}` |
| `/managers/state` | Every task manager's running and waiting tasks, each with its `id`. | |

The main queue is at `/task_manager/...` and its tasks at `/tasks/...`. Another task manager has the same endpoints at `/managers/<name>/...`, and its tasks at `/managers/<name>/tasks/<task>`. The endpoints that take a `task_id` aren't listed at `/docs`.

## Sequences

| Endpoint | Does |
|---|---|
| `/sequences` | The sequences saved, each with its name, when it was saved, and its tasks' names. |
| `/sequences/save?name=cooldown` | Saves the main queue, starting with the running task. `include_running=false` leaves it out, `manager=` saves another task manager's, and `overwrite=true` replaces one of the same name. |
| `/sequences/load?name=cooldown` | Queues the sequence's tasks after those already waiting. `manager=` loads onto another task manager. |
| `/sequences/delete?name=cooldown` | Deletes it. |

## Traces

| Endpoint | Does |
|---|---|
| `/traces` | The experiment's traces. |
| `/traces/<trace>/acquire` | Takes a trace now, and answers once it is taken, with its number. |
| `/traces/<trace>/latest` | The latest trace. |
| `/traces/<trace>/history` | The recent traces, kept for the trace and map panels. |

## The experiment

| Endpoint | Does | Answers, for example |
|---|---|---|
| `/experiment/info` | The experiment's name. | `{"status": 200, "data": {"name": "Lab"}}` |
| `/experiment/shutdown` | Stops the experiment, as closing the window does. | `{"status": "success", "message": "Experiment shutdown initiated."}` |
| `/ping` | Answers while the experiment is running. | `"pong"` |
| `/docs` | Every endpoint, with its inputs, to read and try. | |

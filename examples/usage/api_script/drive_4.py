import time

import requests

LAB = "http://localhost:8000"


def call(path, **params):
    """Calls the experiment's web API, and gives the data it answers."""
    answer = requests.get(f"{LAB}{path}", params=params, timeout=10)
    answer.raise_for_status()
    return answer.json().get("data")


print("The lock-in is at", call("/lockin/get_frequency"), "Hz")

call("/lockin/set_frequency", frequency=211.0)
print("Now it is at", call("/lockin/get_frequency"), "Hz")

call("/tasks/record", files=2, seconds=5)
print("Record is queued")

time.sleep(1)  # for the queue to start it
while call("/task_manager/current_task") or call("/task_manager/task_list"):
    time.sleep(1)
print("The queue is empty")

"""Finding the endpoints of each task manager in the API schema.

The main task manager keeps the original paths, `/task_manager/...` and
`/tasks/...`. Every other task manager has its own, under `/managers/<name>/`.
"""

MAIN = "main"


def management_paths(schema, name: str) -> list:
    """
    The endpoints that control a task manager: pause, resume, abort and so on.

    Args:
        schema (Schema): The API schema.
        name (str): The name of the task manager.
    """
    if name == MAIN:
        return [
            p for path, p in schema.paths.items() if path.startswith("/task_manager")
        ]

    prefix = f"/managers/{name}/"
    tasks = f"{prefix}tasks/"
    return [
        p
        for path, p in schema.paths.items()
        if path.startswith(prefix) and not path.startswith(tasks)
    ]


def control_path(name: str, action: str) -> str:
    """
    The address of an action on a task manager.

    Args:
        name (str): The name of the task manager.
        action (str): `pause`, `resume`, `abort` or `remove_queued_task` or `move_queued_task`.
    """
    if name == MAIN:
        return f"/task_manager/{action}"
    return f"/managers/{name}/{action}"


def task_paths(schema, name: str) -> list:
    """
    The endpoints that queue a registered task on a task manager.

    Args:
        schema (Schema): The API schema.
        name (str): The name of the task manager.
    """
    prefix = "/tasks/" if name == MAIN else f"/managers/{name}/tasks/"
    return [p for path, p in schema.paths.items() if path.startswith(prefix)]

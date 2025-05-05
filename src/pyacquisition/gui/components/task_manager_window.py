import dearpygui.dearpygui as dpg
from .text import add_header
from ..constants import TEXT_COLOR, EMPHASIS_COLOR, SECONDARY_COLOR, WHITE


class TaskManagerWindow:
    def __init__(self):
        self.window_tag = dpg.generate_uuid()

        with dpg.window(
            label="Task Queue",
            width=400,
            height=400,
            pos=[340, 40],
            no_close=True,
            no_collapse=True,
            no_background=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            tag=self.window_tag,
        ):
            self.running_status_uuid = dpg.add_text(
                "Running Status: ", color=(255, 255, 255)
            )
            self.current_task_uuid = dpg.add_text(
                "Current Task: ", color=(255, 255, 255)
            )
            add_header("Queue:", color=(255, 255, 255))
            self.task_queue_uuid = dpg.generate_uuid()

            with dpg.group(tag=self.task_queue_uuid):
                dpg.add_text("-", color=(255, 255, 255))

    def update_running_status(self, status: str) -> None:
        """
        Update the running status in the GUI.

        Args:
            status (str): The running status of the task manager.
        """
        dpg.set_value(self.running_status_uuid, f"Running Status: {status}")

    def update_current_task(self, task_name: str) -> None:
        """
        Update the current task in the GUI.

        Args:
            task_name (str): The name of the current task.
        """
        dpg.set_value(self.current_task_uuid, f"Current Task: {task_name}")

    def update_task_queue(self, tasks: list) -> None:
        """
        Update the task queue in the GUI.

        Args:
            tasks (list): The list of tasks in the queue.
        """

        viewport_height = dpg.get_viewport_client_height()

        dpg.configure_item(self.window_tag, height=viewport_height - 100)

        dpg.delete_item(self.task_queue_uuid)
        self.task_queue_uuid = dpg.generate_uuid()

        with dpg.group(tag=self.task_queue_uuid, parent=self.window_tag):
            for i, task in enumerate(tasks):
                with dpg.group(horizontal=True, parent=self.task_queue_uuid):
                    index_string = f"[{i}]"
                    dpg.add_text(f"{index_string:<5}", color=(255, 255, 255))
                    dpg.add_text(f"{task['name']}", color=EMPHASIS_COLOR)
                with dpg.group(horizontal=True, parent=self.task_queue_uuid):
                    dpg.add_text(
                        f"{task['description']}", color=TEXT_COLOR, wrap=350, indent=42
                    )
                if task["parameters"]:
                    with dpg.group(
                        horizontal=True, parent=self.task_queue_uuid, indent=42
                    ):
                        left_group = dpg.add_group()
                        right_group = dpg.add_group()

                        for j, (param, value) in enumerate(task["parameters"].items()):
                            if j % 2 == 0:
                                with dpg.group(horizontal=True, parent=left_group):
                                    dpg.add_text(f"{param:<10}", color=SECONDARY_COLOR)
                                    dpg.add_text(f"{value:<10}", color=WHITE)
                            else:
                                with dpg.group(horizontal=True, parent=right_group):
                                    dpg.add_text(f"{param:<10}", color=SECONDARY_COLOR)
                                    dpg.add_text(f"{value:<10}", color=WHITE)

                dpg.add_spacer(height=5)

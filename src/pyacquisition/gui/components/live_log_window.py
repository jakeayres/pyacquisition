import dearpygui.dearpygui as dpg
from datetime import datetime


class LiveLogWindow:
    WINDOW_WIDTH = 600

    def __init__(self):
        self.window_tag = dpg.generate_uuid()

        with dpg.window(
            label="Logs",
            width=self.WINDOW_WIDTH,
            no_close=True,
            no_collapse=True,
            no_background=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            tag=self.window_tag,
        ):
            pass

        self.update_layout()

    def update_layout(self):
        """
        Keep the window docked to the right of the viewport.
        """
        viewport_width = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()
        dpg.configure_item(
            self.window_tag,
            pos=[viewport_width - self.WINDOW_WIDTH - 20, 40],
            height=viewport_height - 100,
        )

    def add_log(self, log: dict):
        """
        Append a log message to the window.
        """
        timestamp = datetime.fromtimestamp(log["time"]).strftime("%Y-%m-%d %H:%M:%S")
        with dpg.group(horizontal=True, parent=self.window_tag):
            if log["level"] == "error":
                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                dpg.add_text(f"[{log['level']}]", color=(255, 171, 91))
                dpg.add_text(f"{log['message']}", color=(255, 255, 255))
            elif log["level"] == "warning":
                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                dpg.add_text(f"[{log['level']}]", color=(255, 171, 91))
                dpg.add_text(f"{log['message']}", color=(255, 255, 255))
            elif log["level"] == "info":
                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                dpg.add_text(f"[{log['level']}]", color=(128, 196, 233))
                dpg.add_text(f"{log['message']}", color=(255, 255, 255))
            elif log["level"] == "debug":
                dpg.add_text(f"[{timestamp}]", color=(0, 135, 158))
                dpg.add_text(f"[{log['level']}]", color=(0, 135, 158))
                dpg.add_text(f"{log['message']}", color=(175, 175, 175))
            else:
                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                dpg.add_text(f"[{log['level']}]", color=(128, 196, 233))
                dpg.add_text(f"{log['message']}", color=(255, 255, 255))

import dearpygui.dearpygui as dpg
import time
from ..constants import EMPHASIS_COLOR, SECONDARY_COLOR, WHITE


class LiveDataWindow:
    def __init__(self):
        self.window_tag = dpg.generate_uuid()
        self.time_group_tag = dpg.generate_uuid()
        self.time_tag = dpg.generate_uuid()
        self.key_tags = {}
        self.value_tags = {}
        self._last_update = None

        with dpg.window(
            label="Live Data",
            pos=[20, 140],
            width=300,
            height=750,
            no_close=True,
            no_collapse=True,
            no_background=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            tag=self.window_tag,
        ):
            with dpg.group(horizontal=True, tag=self.time_group_tag):
                dpg.add_text("Loop Time      ", color=EMPHASIS_COLOR)
                dpg.add_text("0.000 s", tag=self.time_tag, color=WHITE)

    def _add_row(self, key: str, value):
        """
        Add a row for a key, above the loop time row.
        """
        with dpg.group(
            horizontal=True, parent=self.window_tag, before=self.time_group_tag
        ):
            tag = dpg.generate_uuid()
            self.key_tags[key] = tag
            dpg.add_text(f"{key:{' '}<{15}}", tag=tag, color=SECONDARY_COLOR)

            tag = dpg.generate_uuid()
            self.value_tags[key] = tag
            dpg.add_text(f"{value:{' '}<{15}}", tag=tag)

    def update(self, data: dict):
        """
        Update the window with a new row of data.
        """
        now = time.time()

        for key, value in data.items():
            if key not in self.key_tags:
                self._add_row(key, value)
            else:
                dpg.set_value(self.value_tags[key], f"{value:{' '}<{15}}")

        if self._last_update is not None:
            dpg.set_value(self.time_tag, f"{now - self._last_update:.3f} s")
        self._last_update = now

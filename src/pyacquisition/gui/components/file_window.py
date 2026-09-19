import dearpygui.dearpygui as dpg
from .header import PaneHeader
from ..constants import SECONDARY_COLOR, WHITE

WINDOW_WIDTH = 300
HEADER_WIDTH = WINDOW_WIDTH - 16  # the width of the window, less its padding


class FileWindow:
    """
    The pane that shows the file that data is being saved to, and its folder.
    """

    def __init__(self):
        self.file_uuid = None
        self.directory_uuid = dpg.generate_uuid()

        with dpg.window(
            label="Current File",
            width=WINDOW_WIDTH,
            height=100,
            pos=[20, 40],
            no_title_bar=True,  # the header is the title
            no_close=True,
            no_collapse=True,
            no_background=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
        ) as window:
            # The name of the file is the title, with a small label above it.
            self.header = PaneHeader(
                window, HEADER_WIDTH, title="-", caption="DATA FILE", style="neutral"
            )
            dpg.add_spacer(height=4)

            with dpg.group(horizontal=True):
                dpg.add_text("Directory:     ", color=SECONDARY_COLOR)
                dpg.add_text("", tag=self.directory_uuid, color=WHITE)

    def update_file(self, file_path: str) -> None:
        """
        Update the file path in the GUI.

        Args:
            file_path (str): The path of the current datafile.
        """
        self.header.update(title=file_path, style="neutral")

    def update_directory(self, directory_path: str) -> None:
        """
        Update the directory path in the GUI.

        Args:
            directory_path (str): The path of the current directory.
        """
        dpg.set_value(self.directory_uuid, directory_path)

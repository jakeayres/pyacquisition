import dearpygui.dearpygui as dpg
from .header import CAPTION_COLOR, PaneHeader
from .styles import arrow_theme, card_themes
from .text import add_header
from ..constants import EMPHASIS_COLOR, SECONDARY_COLOR, TEXT_COLOR, WHITE
from ..managers import MAIN


RUNNING_COLOR = (110, 225, 150)
PAUSED_COLOR = (245, 185, 60)
ABORTING_COLOR = (245, 115, 115)
IDLE_COLOR = (130, 130, 130)

# In a section, the queue is labelled, and there is a clear gap below it so that it
# belongs to its own card and not to the header of the next section.
# The width of the buttons beside a queued task: Remove, and the two arrows.
REMOVE_WIDTH = 66
MOVE_WIDTH = 60
ARROW_WIDTH = 24
ARROW_HEIGHT = 19

GAP_ABOVE_QUEUE = 2
GAP_BELOW_QUEUE = 32

# The width of a header in the Task Queue window. It is adjusted to the window as
# it is updated, for example when a scroll bar appears.
HEADER_WIDTH = 384


def format_value(value) -> str:
    """A parameter as text. Long decimals are shortened, and everything else as is."""
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def add_parameters(parent, parameters: dict, indent: int = 0) -> None:
    """
    Show a task's parameters in two columns.

    Args:
        parent: The item to add them to.
        parameters (dict): Parameter name to value.
        indent (int): How far to indent them.
    """
    with dpg.group(horizontal=True, parent=parent, indent=indent):
        left_group = dpg.add_group()
        right_group = dpg.add_group()

        for j, (param, value) in enumerate(parameters.items()):
            column = left_group if j % 2 == 0 else right_group
            with dpg.group(horizontal=True, parent=column):
                dpg.add_text(f"{param:<10}", color=SECONDARY_COLOR)
                dpg.add_text(f"{format_value(value):<10}", color=WHITE)


def _abort_button_theme():
    """A red theme for the abort button, so that it does not look like the others."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            for column, colour in (
                (dpg.mvThemeCol_Button, (110, 40, 40)),
                (dpg.mvThemeCol_ButtonHovered, (160, 55, 55)),
                (dpg.mvThemeCol_ButtonActive, (190, 70, 70)),
            ):
                dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Core)
    return theme


class TaskManagerPanel:
    """
    One task manager in the window: whether it is running, the task that is
    running, and the tasks waiting behind it.

    Each has a header showing its name, the task that is running and a badge for
    its state, coloured to match: green while running, amber while paused, red while
    it is being aborted, and grey when nothing is running. With several task
    managers the header has a chevron that collapses the section, and the task that
    is running is shown in full in a card of the same colour.
    """

    def __init__(
        self,
        name: str,
        parent,
        stacked: bool,
        on_toggle=None,
        on_abort=None,
        on_remove=None,
        on_move=None,
    ) -> None:
        """
        Args:
            name (str): The name of the task manager.
            parent: The window that holds the panel.
            stacked (bool): Whether the window holds several task managers.
            on_toggle: Called with the name of the task manager, and whether it is
                paused, when its pause or resume button is pressed.
            on_abort: Called with the name of the task manager, and the name of the
                task that is running, when its abort button is pressed.
            on_remove: Called with the name of the task manager, the id of a queued
                task and its name, when the button beside that task is pressed.
            on_move: Called with the name of the task manager, the id of a queued
                task, its name and `up` or `down`, when one of the arrows beside
                that task is pressed.
        """
        self.name = name
        self.stacked = stacked
        self.on_toggle = on_toggle
        self.on_abort = on_abort
        self.on_remove = on_remove
        self.on_move = on_move
        self.remove_tags = {}  # the remove button of each queued task, by its id
        self.move_tags = {}  # the up and down buttons of each queued task, by its id
        self._arrow_theme = arrow_theme()
        self._queue_ids = []  # the ids of the queued tasks, in order
        self._last_state = None
        self._last_queue = None
        self._paused = False
        self._aborting = False
        self._task_name = None

        self.title = name.upper() if stacked else "TASK QUEUE"
        self.header = PaneHeader(
            parent,
            HEADER_WIDTH,
            title=self.title,
            collapsible=stacked,
            on_collapse=self._collapse,
        )

        if stacked:
            # Everything below the header, which the chevron hides.
            self.section_tag = dpg.add_group(parent=parent)
            self.container = self.section_tag
            dpg.add_spacer(height=4, parent=self.section_tag)

            self._themes = card_themes()
            self.card_style = None
            self.card_tag = dpg.add_child_window(
                parent=self.section_tag, width=-1, auto_resize_y=True, border=True
            )
            # The title is on the left and the buttons on the right. The title and
            # the body are rebuilt as the task changes, but the buttons are made
            # once, so that a click is never lost to a refresh part way through.
            with dpg.table(
                parent=self.card_tag,
                header_row=False,
                policy=dpg.mvTable_SizingStretchProp,
                borders_innerH=False,
                borders_innerV=False,
                borders_outerH=False,
                borders_outerV=False,
            ):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=146)
                with dpg.table_row():
                    self.title_tag = dpg.add_group()
                    with dpg.group(horizontal=True):
                        self.toggle_tag = dpg.add_button(
                            label="Pause", width=68, callback=self._toggle
                        )
                        self.abort_tag = dpg.add_button(
                            label="Abort", width=68, callback=self._abort
                        )
            dpg.bind_item_theme(self.abort_tag, _abort_button_theme())
            self.body_tag = dpg.add_group(parent=self.card_tag)
        else:
            self.container = parent
            add_header("Queue:", color=(255, 255, 255))

        self.queue_tag = dpg.generate_uuid()
        with dpg.group(tag=self.queue_tag, parent=self.container):
            dpg.add_text("-", color=(255, 255, 255))

    def update(self, state: dict) -> None:
        """
        Update the panel from a task manager's state.

        Args:
            state (dict): Its `status`, `current_task` and `queue`.
        """
        if state == self._last_state:
            return  # nothing has changed, so do not rebuild the queue
        self._last_state = state

        current = state["current_task"]
        aborting = state.get("aborting", False)

        if aborting:
            style, badge = "aborting", "ABORTING"
        elif state["status"] == "Paused":
            style, badge = "paused", "PAUSED"
        elif current:
            style, badge = "running", "RUNNING"
        else:
            style, badge = "idle", "IDLE"
        self.header.update(
            title=self.title,
            subtitle=current["name"] if current else "nothing running",
            badge=badge,
            style=style,
        )

        if self.stacked:
            self._update_card(state["status"], current, aborting)

        # The queue holds buttons, so it is rebuilt only when it changes. The card is
        # refreshed as the running task's values change, and rebuilding the queue
        # with it could lose a click that straddled a refresh.
        if state["queue"] != self._last_queue:
            self._last_queue = state["queue"]
            self._update_queue(state["queue"])

    def _collapse(self, collapsed: bool) -> None:
        """The chevron in the header was pressed: hide or show the section."""
        dpg.configure_item(self.section_tag, show=not collapsed)

    def _toggle(self, sender=None, app_data=None, user_data=None) -> None:
        """The pause or resume button was pressed."""
        if self.on_toggle:
            self.on_toggle(self.name, self._paused)

    def _abort(self, sender=None, app_data=None, user_data=None) -> None:
        """The abort button was pressed."""
        if self._task_name is not None and not self._aborting and self.on_abort:
            self.on_abort(self.name, self._task_name)

    def _update_card(
        self, status: str, task: dict | None, aborting: bool = False
    ) -> None:
        """
        Show the task that is running in full, in a card that shows its state.

        Args:
            status (str): `Running` or `Paused`.
            task (dict | None): The running task's name, description and
                parameters, or `None` if nothing is running.
            aborting (bool): Whether the task has been told to stop, and has not
                finished yet.
        """
        if task is None:
            style = "idle"
        elif aborting:
            style = "aborting"
        else:
            style = "paused" if status == "Paused" else "running"

        if style != self.card_style:
            dpg.bind_item_theme(self.card_tag, self._themes[style])
            self.card_style = style

        self._paused = status == "Paused"
        self._task_name = task["name"] if task else None
        self._aborting = aborting
        dpg.configure_item(self.toggle_tag, label="Resume" if self._paused else "Pause")
        # There is nothing to abort unless a task is running, and nothing more to do
        # once it has been told to stop.
        dpg.configure_item(self.abort_tag, enabled=task is not None and not aborting)

        dpg.delete_item(self.title_tag, children_only=True)
        dpg.delete_item(self.body_tag, children_only=True)

        if task is None:
            what = "Paused" if self._paused else "Idle"
            dpg.add_text(
                f"{what}: nothing is running", color=IDLE_COLOR, parent=self.title_tag
            )
            return

        badge, colour = {
            "running": ("RUNNING", RUNNING_COLOR),
            "paused": ("PAUSED", PAUSED_COLOR),
            "aborting": ("ABORTING", ABORTING_COLOR),
        }[style]
        with dpg.group(horizontal=True, parent=self.title_tag):
            dpg.add_text(badge, color=colour)
            dpg.add_text(task["name"], color=WHITE)
        if task["description"]:
            dpg.add_text(
                f"{task['description']}",
                color=TEXT_COLOR,
                wrap=340,
                parent=self.body_tag,
            )
        if task["parameters"]:
            add_parameters(self.body_tag, task["parameters"])

    def _remove(self, sender=None, app_data=None, user_data=None) -> None:
        """The remove button beside a queued task was pressed."""
        task_id, task_name = user_data
        if self.on_remove:
            self.on_remove(self.name, task_id, task_name)

    def _move(self, sender=None, app_data=None, user_data=None) -> None:
        """An arrow beside a queued task was pressed."""
        task_id, task_name, direction = user_data
        if task_id not in self._queue_ids:
            return
        index = self._queue_ids.index(task_id)
        # The place in front of the first task is the running task's, and there is
        # nothing after the last, so neither way is open there. The arrow is greyed
        # out too, but this must hold whatever calls it.
        if direction == "up" and index == 0:
            return
        if direction == "down" and index == len(self._queue_ids) - 1:
            return
        if self.on_move:
            self.on_move(self.name, task_id, task_name, direction)

    def _update_queue(self, tasks: list) -> None:
        dpg.delete_item(self.queue_tag)
        self.queue_tag = dpg.generate_uuid()
        self.remove_tags = {}
        self.move_tags = {}
        self._queue_ids = [task.get("id") for task in tasks]

        with dpg.group(tag=self.queue_tag, parent=self.container):
            if self.stacked:
                dpg.add_spacer(height=GAP_ABOVE_QUEUE)
                with dpg.group(horizontal=True):
                    dpg.add_text("QUEUE", color=CAPTION_COLOR)
                    dpg.add_text(
                        f"{len(tasks)} waiting" if tasks else "empty", color=IDLE_COLOR
                    )
                dpg.add_spacer(height=4)

            for i, task in enumerate(tasks):
                # The task on the left and its buttons on the right. The task is
                # picked out by its id, not its position, because the queue may have
                # moved on since it was drawn.
                with dpg.table(
                    parent=self.queue_tag,
                    header_row=False,
                    policy=dpg.mvTable_SizingStretchProp,
                    borders_innerH=False,
                    borders_innerV=False,
                    borders_outerH=False,
                    borders_outerV=False,
                ):
                    dpg.add_table_column(width_stretch=True)
                    dpg.add_table_column(
                        width_fixed=True,
                        init_width_or_weight=REMOVE_WIDTH
                        + (MOVE_WIDTH if self.on_move else 0),
                    )
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            index_string = f"[{i}]"
                            dpg.add_text(f"{index_string:<5}", color=(255, 255, 255))
                            dpg.add_text(f"{task['name']}", color=EMPHASIS_COLOR)
                        with dpg.group(horizontal=True):
                            task_id = task.get("id")
                            if self.on_move and task_id:
                                # The first task cannot go up, because the place in
                                # front of it is the running task's. The last cannot
                                # go down.
                                up = dpg.add_button(
                                    arrow=True,
                                    direction=dpg.mvDir_Up,
                                    width=ARROW_WIDTH,
                                    height=ARROW_HEIGHT,
                                    enabled=i > 0,
                                    callback=self._move,
                                    user_data=(task_id, task["name"], "up"),
                                )
                                down = dpg.add_button(
                                    arrow=True,
                                    direction=dpg.mvDir_Down,
                                    width=ARROW_WIDTH,
                                    height=ARROW_HEIGHT,
                                    enabled=i < len(tasks) - 1,
                                    callback=self._move,
                                    user_data=(task_id, task["name"], "down"),
                                )
                                dpg.bind_item_theme(up, self._arrow_theme)
                                dpg.bind_item_theme(down, self._arrow_theme)
                                self.move_tags[task_id] = (up, down)
                            if self.on_remove and task_id:
                                self.remove_tags[task_id] = dpg.add_button(
                                    label="Remove",
                                    small=True,
                                    callback=self._remove,
                                    user_data=(task_id, task["name"]),
                                )
                with dpg.group(horizontal=True, parent=self.queue_tag):
                    dpg.add_text(
                        f"{task['description']}", color=TEXT_COLOR, wrap=350, indent=42
                    )
                if task["parameters"]:
                    add_parameters(self.queue_tag, task["parameters"], indent=42)

                dpg.add_spacer(height=5)

            if self.stacked:
                dpg.add_spacer(height=GAP_BELOW_QUEUE)


class TaskManagerWindow:
    """
    The Task Queue window. It shows every task manager of the experiment.
    """

    def __init__(
        self, names=(MAIN,), on_toggle=None, on_abort=None, on_remove=None, on_move=None
    ):
        """
        Args:
            names: The names of the task managers, in the order to show them.
            on_toggle: Called with the name of a task manager, and whether it is
                paused, when the pause or resume button of its card is pressed.
            on_abort: Called with the name of a task manager, and the name of the
                task that it is running, when the abort button of its card is
                pressed.
            on_remove: Called with the name of a task manager, the id of a queued
                task and its name, when the button beside that task is pressed.
            on_move: Called with the name of a task manager, the id of a queued task,
                its name and `up` or `down`, when an arrow beside that task is
                pressed.
        """
        self.window_tag = dpg.generate_uuid()
        stacked = len(names) > 1

        with dpg.window(
            label="Task Queue",
            width=400,
            height=400,
            pos=[340, 40],
            no_title_bar=True,  # the headers of the task managers are the titles
            no_close=True,
            no_collapse=True,
            no_background=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            tag=self.window_tag,
        ):
            self.panels = {
                name: TaskManagerPanel(
                    name,
                    self.window_tag,
                    stacked,
                    on_toggle,
                    on_abort,
                    on_remove,
                    on_move,
                )
                for name in names
            }

    def update(self, states: dict) -> None:
        """
        Update the window.

        Args:
            states (dict): The state of every task manager, by name.
        """
        viewport_height = dpg.get_viewport_client_height()
        dpg.configure_item(self.window_tag, height=viewport_height - 100)

        for name, panel in self.panels.items():
            panel.header.fit_to(self.window_tag)
            if name in states:
                panel.update(states[name])

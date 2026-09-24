import dearpygui.dearpygui as dpg
from .header import CAPTION_COLOR, PaneHeader
from .add_card import AddCard
from .fonts import add_font
from .pane import CARD_SPACING, fit_to_page
from .styles import arrow_theme, compact_theme
from ..constants import (
    QUEUED_ACCENT,
    QUEUED_BACKGROUND,
    SECONDARY_COLOR,
    STATE_STYLES,
    DEFAULT_PAGE_WIDTH,
    PANE_X,
    TOP_Y,
    TEXT_COLOR,
    WHITE,
)
from ..managers import MAIN


RUNNING_COLOR = (110, 225, 150)
PAUSED_COLOR = (245, 185, 60)
ABORTING_COLOR = (245, 115, 115)
IDLE_COLOR = (130, 130, 130)

# In a section, there is a gap below the queue, so that it belongs to its own card and
# not to the header of the next section.
# The width of the buttons beside a queued task: Remove, and the two arrows.
X_SIZE = 18  # the red square with an X, which removes a task or aborts it
ARROW_WIDTH = X_SIZE  # so that the X and the arrows are one column
ARROW_HEIGHT = 9  # two arrows, one above the other, are about as tall as the square
COLUMN_GAP = 6
BUTTONS_WIDTH = X_SIZE  # the X, with the two arrows under it, in one column
X_ARROW_GAP = 6  # between the bottom of the X and the top of the up arrow

# A queued task is a grey card with a bold edge at its left. Its lines are packed close
# together, because the queue can be long.
ACCENT_WIDTH = 5
CARD_PAD_X = 8
CARD_PAD_Y = 3
DETAIL_INDENT = 40  # the description and inputs are under the name, not the number
DESCRIPTION_WRAP = 300

GAP_BELOW_QUEUE = 16

# The width of a header in the Task Queue window. It is adjusted to the window as
# it is updated, for example when a scroll bar appears.
HEADER_WIDTH = DEFAULT_PAGE_WIDTH - 16  # until it is laid out: the window, less its padding
TITLE_FONT_SIZE = 20  # the title of a header, as in the Live Data window
HEADER_STYLES = {  # how a header shows the state: only a task in trouble is coloured
    "running": ("idle", None),
    "idle": ("idle", None),
    "paused": ("paused", "PAUSED"),
    "aborting": ("aborting", "ABORTING"),
}


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


def _x_button_theme():
    """A theme for the buttons that end a task: a red square, with a white X."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            for column, colour in (
                (dpg.mvThemeCol_Button, (200, 55, 55)),
                (dpg.mvThemeCol_ButtonHovered, (228, 84, 84)),
                (dpg.mvThemeCol_ButtonActive, (245, 110, 110)),
                (dpg.mvThemeCol_Text, WHITE),
            ):
                dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(
                dpg.mvStyleVar_FrameRounding, 0, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_FramePadding, 0, 0, category=dpg.mvThemeCat_Core
            )
        with dpg.theme_component(dpg.mvButton, enabled_state=False):
            dpg.add_theme_color(
                dpg.mvThemeCol_Button, (70, 40, 40), category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_Text, (130, 130, 130), category=dpg.mvThemeCat_Core
            )
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
        title_font=None,
        tasks=None,
        on_add=None,
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
            title_font: The font of the title of the header, or `None` for the
                default font.
            tasks: The tasks that can be added to its queue, as the endpoints that add
                them. Without any there is no card for adding one.
            on_add: Called with the name of the task manager, and the endpoint of the
                task that was picked, when a task is picked from the list that the card
                for adding one shows.
        """
        self.name = name
        self.stacked = stacked
        self.on_toggle = on_toggle
        self.on_abort = on_abort
        self.on_remove = on_remove
        self.on_move = on_move
        self.tasks = tasks or []
        self.on_add = on_add
        self.add_menu_tag = None  # the list of tasks to add, made when it is first shown
        self.remove_tags = {}  # the remove button of each queued task, by its id
        self.move_tags = {}  # the up and down buttons of each queued task, by its id
        self._arrow_theme = arrow_theme()
        self._x_theme = _x_button_theme()
        self._card_theme = compact_theme()
        self.card_tags = []  # the card of each queued task, in order
        self._queue_ids = []  # the ids of the queued tasks, in order
        self._last_state = None
        self._last_queue = None
        self._paused = False
        self._aborting = False
        self._task_name = None

        self.title = name[:1].upper() + name[1:] if stacked else "Task Queue"
        self.header = PaneHeader(
            parent,
            HEADER_WIDTH,
            title=self.title,
            collapsible=stacked,
            on_collapse=self._collapse,
            on_action=self._toggle,
            flat=True,
            title_font=title_font,
            title_size=TITLE_FONT_SIZE,
        )

        # Everything below the header, which the chevron hides if there are several
        # task managers.
        self.section_tag = dpg.add_group(parent=parent)
        self.container = self.section_tag
        # The task that is running, in a card like a queued task's, but in the colour of
        # its state, however many task managers there are: a strip of the colour at the
        # left, and a tint behind the text, which are two cells of a table.
        self.card_style = None
        self.card_colors = None  # the strip and the tint, as last drawn
        self._card_theme = compact_theme()
        self.card_tag = dpg.add_table(
            parent=self.section_tag,
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            borders_innerH=False,
            borders_innerV=False,
            borders_outerH=False,
            borders_outerV=False,
        )
        dpg.add_table_column(width_fixed=True, init_width_or_weight=ACCENT_WIDTH, parent=self.card_tag)
        dpg.add_table_column(width_stretch=True, parent=self.card_tag)
        with dpg.table_row(parent=self.card_tag):
            dpg.add_spacer(width=ACCENT_WIDTH, height=1)
            with dpg.group(indent=CARD_PAD_X) as content:
                dpg.add_spacer(height=CARD_PAD_Y)
                # The title is on the left and the buttons on the right. The title
                # and the body are rebuilt as the task changes, but the buttons are
                # made once, so that a click is never lost to a refresh part way
                # through.
                with dpg.table(
                    header_row=False,
                    policy=dpg.mvTable_SizingStretchProp,
                    borders_innerH=False,
                    borders_innerV=False,
                    borders_outerH=False,
                    borders_outerV=False,
                ):
                    dpg.add_table_column(width_stretch=True)
                    dpg.add_table_column(
                        width_fixed=True, init_width_or_weight=X_SIZE + COLUMN_GAP
                    )
                    with dpg.table_row():
                        self.title_tag = dpg.add_group()
                        self.abort_tag = dpg.add_button(
                            label="X", width=X_SIZE, height=X_SIZE, callback=self._abort
                        )
                dpg.bind_item_theme(self.abort_tag, self._x_theme)
                self.body_tag = dpg.add_group()
                dpg.add_spacer(height=CARD_PAD_Y)
        dpg.bind_item_theme(self.card_tag, self._card_theme)

        # A line under the card, like the one under the header, which sets the running
        # task apart from the ones waiting.
        self._rule_list = dpg.add_drawlist(
            width=HEADER_WIDTH, height=1, parent=self.section_tag
        )
        self._rule = dpg.draw_line(
            (0, 0), (HEADER_WIDTH, 0), thickness=1, parent=self._rule_list
        )

        self.queue_tag = dpg.generate_uuid()
        dpg.add_group(tag=self.queue_tag, parent=self.container)

        # At the bottom of the queue is a blank card with a + in it, that shows a list of
        # the tasks that can be added. The queue is rebuilt in front of what follows it.
        self.add_card = None
        if self.tasks and on_add:
            self.add_card = AddCard(
                self.section_tag, HEADER_WIDTH, on_click=self._show_add_menu
            )
        # And below it, a gap, so that the queue belongs to its own card and not to the
        # header of the next section.
        self.gap_tag = None
        if stacked:
            self.gap_tag = dpg.add_spacer(height=GAP_BELOW_QUEUE, parent=self.section_tag)

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
        header_style, header_badge = HEADER_STYLES[style]
        self.header.update(
            title=self.title,
            subtitle=current["name"] if current else "nothing running",
            badge=header_badge,
            style=header_style,
        )
        dpg.configure_item(self._rule, color=STATE_STYLES[header_style]["border"])

        self._update_card(state["status"], current, aborting)

        # The queue holds buttons, so it is rebuilt only when it changes. The card is
        # refreshed as the running task's values change, and rebuilding the queue
        # with it could lose a click that straddled a refresh.
        if state["queue"] != self._last_queue:
            self._last_queue = state["queue"]
            self._update_queue(state["queue"])

    def fit(self) -> None:
        """Make the line under the card as wide as the header, which follows the window."""
        width = self.header.width
        if dpg.get_item_configuration(self._rule_list)["width"] != width:
            dpg.configure_item(self._rule_list, width=width)
            dpg.configure_item(self._rule, p2=(width, 0))

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
            colors = STATE_STYLES[style]
            self.card_colors = (colors["border"], colors["background"])
            dpg.highlight_table_cell(self.card_tag, 0, 0, self.card_colors[0])
            dpg.highlight_table_cell(self.card_tag, 0, 1, self.card_colors[1])
            self.card_style = style

        self._paused = status == "Paused"
        self._task_name = task["name"] if task else None
        self._aborting = aborting
        self.header.set_action("play" if self._paused else "pause")
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

    def _add_queued_task(self, i: int, task: dict, count: int) -> None:
        """
        Add a card for a task that is waiting: its place in the queue, its name and its
        buttons, and under them what it is and what it will be given.

        The card is a table of two cells. The first is narrow, and filled with a bold
        colour, which is the edge of the card. The second is filled grey, and holds
        the text, packed close.

        Args:
            i (int): Its place in the queue, counting from 0.
            task (dict): Its `name`, `description`, `parameters` and `id`.
            count (int): How many tasks are in the queue.
        """
        task_id = task.get("id")
        with dpg.table(
            parent=self.queue_tag,
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            borders_innerH=False,
            borders_innerV=False,
            borders_outerH=False,
            borders_outerV=False,
        ) as card:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=ACCENT_WIDTH)
            dpg.add_table_column(width_stretch=True)
            with dpg.table_row():
                dpg.add_spacer(width=ACCENT_WIDTH, height=1)  # the edge, coloured below
                with dpg.group(indent=CARD_PAD_X) as content:
                    dpg.add_spacer(height=CARD_PAD_Y)

                    # The task on the left and its buttons on the right. The task is
                    # picked out by its id, not its position, because the queue may
                    # have moved on since it was drawn.
                    with dpg.table(
                        header_row=False,
                        policy=dpg.mvTable_SizingStretchProp,
                        borders_innerH=False,
                        borders_innerV=False,
                        borders_outerH=False,
                        borders_outerV=False,
                    ):
                        dpg.add_table_column(width_stretch=True)
                        dpg.add_table_column(
                            width_fixed=True, init_width_or_weight=BUTTONS_WIDTH + COLUMN_GAP
                        )
                        with dpg.table_row():
                            # The name, and under it what the task is and what it will
                            # be given, beside the buttons and not under them.
                            with dpg.group() as text:
                                with dpg.group(horizontal=True):
                                    index_string = f"[{i}]"
                                    dpg.add_text(f"{index_string:<5}", color=WHITE)
                                    dpg.add_text(f"{task['name']}", color=WHITE)
                                if task["description"]:
                                    dpg.add_text(
                                        f"{task['description']}",
                                        color=TEXT_COLOR,
                                        wrap=DESCRIPTION_WRAP,
                                        indent=DETAIL_INDENT,
                                    )
                                if task["parameters"]:
                                    add_parameters(text, task["parameters"], DETAIL_INDENT)
                            with dpg.group():
                                self._add_queued_buttons(i, task, count)

                    dpg.add_spacer(height=CARD_PAD_Y)

        dpg.highlight_table_cell(card, 0, 0, QUEUED_ACCENT)
        dpg.highlight_table_cell(card, 0, 1, QUEUED_BACKGROUND)
        dpg.bind_item_theme(card, self._card_theme)
        self.card_tags.append(card)

    def _add_queued_buttons(self, i: int, task: dict, count: int) -> None:
        """
        Add the buttons beside a queued task: a red X that removes it, with the arrows that
        move it under it, one above the other, all in one column.
        Only tasks that have an id can be picked out to act on.
        """
        task_id = task.get("id")
        # The X is at the top right, with the arrows under it.
        with dpg.group():
            if self.on_remove and task_id:
                self.remove_tags[task_id] = dpg.add_button(
                    label="X",
                    width=X_SIZE,
                    height=X_SIZE,
                    callback=self._remove,
                    user_data=(task_id, task["name"]),
                )
                dpg.bind_item_theme(self.remove_tags[task_id], self._x_theme)
            if self.on_move and task_id:
                # The first task cannot go up, because the place in front of it is
                # the running task's. The last cannot go down.
                dpg.add_spacer(height=X_ARROW_GAP)
                with dpg.group():
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
                        enabled=i < count - 1,
                        callback=self._move,
                        user_data=(task_id, task["name"], "down"),
                    )
                dpg.bind_item_theme(up, self._arrow_theme)
                dpg.bind_item_theme(down, self._arrow_theme)
                self.move_tags[task_id] = (up, down)

    def _update_queue(self, tasks: list) -> None:
        dpg.delete_item(self.queue_tag)
        self.queue_tag = dpg.generate_uuid()
        self.card_tags = []
        self.remove_tags = {}
        self.move_tags = {}
        self._queue_ids = [task.get("id") for task in tasks]

        after = self.add_card.drawlist if self.add_card else (self.gap_tag or 0)
        with dpg.group(tag=self.queue_tag, parent=self.container, before=after):
            for i, task in enumerate(tasks):
                self._add_queued_task(i, task, len(tasks))

    def _show_add_menu(self) -> None:
        """
        Show the list of tasks that can be added, next to the mouse. It closes when
        something else is clicked, or when a task is picked.
        """
        if self.add_menu_tag is None:
            self.add_menu_tag = self._make_add_menu()
        dpg.configure_item(
            self.add_menu_tag, pos=dpg.get_mouse_pos(local=False), show=True
        )

    def _make_add_menu(self):
        """The list of tasks that can be added, as a window that is a popup."""
        with dpg.window(
            popup=True,
            show=False,
            no_title_bar=True,
            no_move=True,
            autosize=True,
            min_size=(180, 40),
        ) as menu:
            dpg.add_text("ADD A TASK", color=CAPTION_COLOR)
            dpg.add_separator()
            self.add_items = {}
            for path in self.tasks:
                self.add_items[path.path] = dpg.add_selectable(
                    label=f" {path.get.summary}",
                    callback=self._picked,
                    user_data=path,
                    span_columns=True,
                )
        return menu

    def _picked(self, sender=None, app_data=None, user_data=None) -> None:
        """A task was picked from the list: close it, and add the task."""
        dpg.set_value(sender, False)
        dpg.configure_item(self.add_menu_tag, show=False)
        if self.on_add:
            self.on_add(self.name, user_data)

    def tick(self) -> None:
        """Call this each frame, for the card for adding a task to light up."""
        if self.add_card:
            self.add_card.tick()

    def fit_add_card(self) -> None:
        """Keep the card for adding a task as wide as the header."""
        if self.add_card and self.add_card.width != self.header.width:
            self.add_card.resize(self.header.width)


class TaskManagerWindow:
    """
    The Task Queue window. It shows every task manager of the experiment.
    """

    def __init__(
        self,
        names=(MAIN,),
        on_toggle=None,
        on_abort=None,
        on_remove=None,
        on_move=None,
        tasks=None,
        on_add=None,
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
            tasks: The endpoints that add each task, by the name of the task manager
                whose queue they add to. A task manager with none has no card for
                adding one.
            on_add: Called with the name of a task manager, and the endpoint of the task
                that was picked, when one is picked from the list of tasks to add.
        """
        self.window_tag = dpg.generate_uuid()
        stacked = len(names) > 1
        # The font has to be loaded before the window is first shown.
        title_font = add_font(TITLE_FONT_SIZE)

        with dpg.window(
            label="Task Queue",
            width=DEFAULT_PAGE_WIDTH,
            height=400,
            pos=[PANE_X, TOP_Y],
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
            # The cards are as close as those of the Live Data window.
            with dpg.theme() as self._spacing_theme:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_style(
                        dpg.mvStyleVar_ItemSpacing,
                        6,
                        CARD_SPACING,
                        category=dpg.mvThemeCat_Core,
                    )
            dpg.bind_item_theme(self.window_tag, self._spacing_theme)
            self.panels = {
                name: TaskManagerPanel(
                    name,
                    self.window_tag,
                    stacked,
                    on_toggle,
                    on_abort,
                    on_remove,
                    on_move,
                    title_font,
                    (tasks or {}).get(name),
                    on_add,
                )
                for name in names
            }

    def update_layout(self) -> None:
        """
        Keep the window in the left part of the viewport, beside the menu, as wide as a
        page and as tall as the viewport, with the headers and cards as wide as it.
        """
        fit_to_page(self.window_tag)
        dpg.configure_item(
            self.window_tag,
            pos=[PANE_X, TOP_Y],
            height=max(dpg.get_viewport_client_height() - TOP_Y - 20, 100),
        )
        for panel in self.panels.values():
            panel.header.fit_to(self.window_tag)
            panel.fit()
            panel.fit_add_card()

    def tick(self) -> None:
        """Call this each frame: keep to the window, and let the cards for adding a task
        light up."""
        self.update_layout()
        for panel in self.panels.values():
            panel.tick()

    def update(self, states: dict) -> None:
        """
        Update the window.

        Args:
            states (dict): The state of every task manager, by name.
        """
        self.update_layout()
        for name, panel in self.panels.items():
            if name in states:
                panel.update(states[name])

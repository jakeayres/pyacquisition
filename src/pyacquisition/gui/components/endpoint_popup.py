import json
from datetime import datetime

import dearpygui.dearpygui as dpg

from ..api_client import Reply
from ..constants import (
    ERROR_COLOR,
    MUTED_COLOR,
    OK_COLOR,
    SECONDARY_COLOR,
    TEXT_COLOR,
    WHITE,
)
from .header import CHAR_WIDTH, PaneHeader
from .input_group import InputGroup
from .inputs.base_input import BaseInput
from .inputs.boolean_input import BooleanInput
from .inputs.enum_input import EnumInput
from .inputs.float_input import FloatInput
from .inputs.integer_input import IntegerInput
from .inputs.string_input import StringInput
from .styles import card_themes, primary_button_theme

WINDOW_WIDTH = 380
CONTENT_WIDTH = WINDOW_WIDTH - 16  # the width of the window, less its padding

# A reply is shown in a card that grows to fit it, so what is shown is kept short.
# The whole reply is always available from the Copy button.
MAX_ROWS = 10
MAX_TEXT = 360


def caption_for(path: str, manager: str | None = None) -> str:
    """
    The small label above the name of an endpoint: what it belongs to.

    Args:
        path (str): The address of the endpoint, such as `/keithley/get_voltage`.
        manager (str | None): The task manager it is for, if the endpoint is one of
            a task manager's. The addresses of the main task manager do not say so.
    """
    parts = [part for part in path.split("/") if part]
    if not parts:
        return "API"
    if parts[0] not in ("managers", "task_manager", "tasks"):
        return parts[0].upper()

    if parts[0] == "managers" and len(parts) > 2:
        manager = manager or parts[1]
        is_task = parts[2] == "tasks"
    else:
        is_task = parts[0] == "tasks"
    kind = "TASKS" if is_task else "TASK MANAGER"
    return f"{manager.upper()} · {kind}" if manager else kind


def unwrap(payload):
    """
    The value in a reply. The server wraps every value as `{"status": 200, "data":
    value}`, which is noise in a window that already says whether it worked.
    """
    if (
        isinstance(payload, dict)
        and "data" in payload
        and set(payload) <= {"status", "data"}
    ):
        return payload["data"]
    return payload


def is_scalar(value) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def scalar_text(value) -> str:
    """A single value as text: long decimals are shortened, and `None` is `None`."""
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def cell_text(value) -> str:
    """One entry of a list or dictionary, on a line of its own."""
    return scalar_text(value) if is_scalar(value) else json.dumps(value)


def rows_of(value) -> list | None:
    """
    A dictionary, or a list, as rows of a name and a value, or `None` if the value
    is not either, or has nothing in it.
    """
    if isinstance(value, dict) and value:
        return [(str(key), cell_text(item)) for key, item in value.items()]
    if isinstance(value, list) and value:
        return [(f"[{i}]", cell_text(item)) for i, item in enumerate(value)]
    return None


def copy_text(value) -> str:
    """Everything in a value, as text, for the clipboard."""
    if isinstance(value, str):
        return value
    if is_scalar(value):
        return scalar_text(value)
    return json.dumps(value, indent=2)


def describe(description: str | None) -> tuple[str, str]:
    """
    Split a description into the part to show and the whole. A docstring is a
    sentence, and then sections such as `Args:`, which are too long for the window.

    Returns:
        tuple[str, str]: The first paragraph, on one line, and the whole text.
    """
    text = (description or "").strip()
    first = text.split("\n\n")[0]
    return " ".join(first.split()), text


def cell_room(name_width: int) -> int:
    """
    How many characters of a value fit on a line of the reply card, beside a name.
    The card is a fixed width, and anything wider than it is cut off.
    """
    return max(12, (CONTENT_WIDTH - 24) // CHAR_WIDTH - name_width - 1)


def elapsed_text(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.2f} s"


class EndpointPopup:
    """
    A window for calling one endpoint of the API.

    A header names the endpoint, a form has a row for each of its parameters, and
    **Send Request** sends them. The reply appears in a card underneath, coloured
    green if it worked and red if it did not. Before anything is sent there is no
    card, so the window is only as big as the form.

    The request is made in the background, so a slow instrument does not freeze the
    interface.
    """

    def __init__(self, api_client, path, manager: str | None = None) -> None:
        self.uuid = dpg.generate_uuid()
        self.api_client = api_client
        self.path = path
        self.title = path.get.summary or path.path.rsplit("/", 1)[-1]
        self.caption = caption_for(path.path, manager)
        self.input_group = InputGroup()
        self.sending = False
        self.last_reply = None  # the last `Reply`, as shown
        self._copy_text = ""
        self._themes = {}
        self._extra_themes = []  # made for this window, and deleted with it
        self.send_tag = None
        self.result_tag = None

        for param in self.path.get.parameters.values():
            self.input_group.add_input(self.param_to_input(param))

    def param_to_input(self, param) -> BaseInput:
        """Convert a parameter type to the corresponding input component."""
        if param.type_ == "integer":
            component = IntegerInput(param.name, default_value=0)
        elif param.type_ == "number":
            component = FloatInput(param.name, default_value=0.0)
        elif param.type_ == "boolean":
            component = BooleanInput(param.name, default_value=False)
        elif param.type_ == "enum":
            component = EnumInput(
                param.name,
                options=param.enum_values,
                default_value=param.enum_values[0],
            )
        else:
            # Text can be sent for anything, and the server says if it is wrong.
            component = StringInput(param.name, default_value="")

        component.hint = f"{param.type_ or 'text'}" + (
            ", required" if param.required else ""
        )
        return component

    @property
    def is_open(self) -> bool:
        """Whether the window is showing."""
        return dpg.does_item_exist(self.uuid)

    def focus(self) -> None:
        """Bring the window to the front."""
        if self.is_open:
            dpg.focus_item(self.uuid)

    def close(self, sender=None, app_data=None, user_data=None) -> None:
        """Close the window, and delete the themes that it made."""
        if self.is_open:
            dpg.delete_item(self.uuid)
        for theme in [*self._themes.values(), *self._extra_themes]:
            if dpg.does_item_exist(theme):
                dpg.delete_item(theme)
        self._themes, self._extra_themes = {}, []

    def draw(self, pos: tuple[int, int] | None = None) -> None:
        """
        Draw the window.

        Args:
            pos (tuple[int, int] | None): Where to put its top left corner.
        """
        self._themes = card_themes()
        with dpg.theme() as self._compact:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(
                    dpg.mvStyleVar_ItemSpacing, 8, 3, category=dpg.mvThemeCat_Core
                )
        primary = primary_button_theme()
        self._extra_themes = [self._compact, primary]
        options = {"pos": list(pos)} if pos is not None else {}

        with dpg.window(
            label=self.path.path,  # the address, for anyone who wants it
            width=WINDOW_WIDTH,
            autosize=True,
            no_collapse=True,
            on_close=self.close,
            tag=self.uuid,
            **options,
        ):
            PaneHeader(
                self.uuid,
                CONTENT_WIDTH,
                title=self.title,
                caption=self.caption,
                style="neutral",
            )

            summary, whole = describe(self.path.get.description)
            if summary:
                dpg.add_spacer(height=4)
                text = dpg.add_text(summary, wrap=CONTENT_WIDTH, color=TEXT_COLOR)
                if whole != summary:
                    with dpg.tooltip(text):
                        dpg.add_text(whole, wrap=420)

            dpg.add_spacer(height=6)
            if self.input_group.length > 0:
                self.input_group.draw()
                dpg.add_spacer(height=6)

            self.send_tag = dpg.add_button(
                label="Send Request",
                width=CONTENT_WIDTH,
                height=28,
                callback=self.request,
            )
            dpg.bind_item_theme(self.send_tag, primary)

            dpg.add_spacer(height=6)
            self.result_tag = dpg.add_child_window(
                width=CONTENT_WIDTH, auto_resize_y=True, border=True, show=False
            )

    def get_input_data(self) -> dict:
        """Retrieve data from all inputs."""
        return self.input_group.get_data()

    def request(self, sender=None, app_data=None, user_data=None) -> None:
        """
        Send a request to the endpoint with the input data. It does not wait for the
        answer: `show_reply` is called when it arrives.
        """
        if self.sending or not self.is_open:
            return
        self.sending = True
        dpg.configure_item(self.send_tag, label="Sending...", enabled=False)
        self.api_client.get_async(
            self.path.path, self.show_reply, params=self.get_input_data()
        )

    def show_reply(self, reply: Reply) -> None:
        """
        Show what came back, in the card under the button.

        Args:
            reply (Reply): The answer to the request, or what went wrong.
        """
        self.sending = False
        if not self.is_open:
            return  # closed while the request was out
        dpg.configure_item(self.send_tag, label="Send Request", enabled=True)
        self.last_reply = reply

        value = unwrap(reply.data) if reply.ok else reply.error
        self._copy_text = copy_text(value)

        dpg.bind_item_theme(
            self.result_tag, self._themes["running" if reply.ok else "aborting"]
        )
        dpg.delete_item(self.result_tag, children_only=True)
        dpg.configure_item(self.result_tag, show=True)

        with dpg.table(
            parent=self.result_tag,
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            borders_innerH=False,
            borders_innerV=False,
            borders_outerH=False,
            borders_outerV=False,
        ):
            dpg.add_table_column(width_stretch=True)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=52)
            with dpg.table_row():
                with dpg.group(horizontal=True):
                    dpg.add_text(
                        "OK" if reply.ok else "ERROR",
                        color=OK_COLOR if reply.ok else ERROR_COLOR,
                    )
                    dpg.add_text(
                        f"{elapsed_text(reply.elapsed)} · "
                        f"{datetime.now().strftime('%H:%M:%S')}",
                        color=MUTED_COLOR,
                    )
                dpg.add_button(label="Copy", small=True, callback=self._copy)

        dpg.add_spacer(height=2, parent=self.result_tag)
        body = dpg.add_group(parent=self.result_tag)
        dpg.bind_item_theme(body, self._compact)
        if reply.ok:
            self._add_value(value, body)
        else:
            dpg.add_text(shorten(value, MAX_TEXT), wrap=CONTENT_WIDTH - 24, parent=body)

    def _add_value(self, value, parent) -> None:
        """Show a value: a list or dictionary as rows, and anything else as text."""
        rows = rows_of(value)
        if rows is None:
            # A single value, or an empty list or dictionary.
            text = scalar_text(value) if is_scalar(value) else json.dumps(value)
            dpg.add_text(
                shorten(text, MAX_TEXT), wrap=CONTENT_WIDTH - 24, parent=parent
            )
            return

        shown = rows[:MAX_ROWS]
        width = max(len(name) for name, _ in shown)  # so that the values line up
        room = cell_room(width)
        for name, text in shown:
            with dpg.group(horizontal=True, parent=parent):
                dpg.add_text(f"{name:<{width}}", color=SECONDARY_COLOR)
                dpg.add_text(shorten(text, room), color=WHITE)
        if len(rows) > MAX_ROWS:
            dpg.add_text(
                f"and {len(rows) - MAX_ROWS} more. Copy has them all.",
                color=MUTED_COLOR,
                parent=parent,
            )

    def _copy(self, sender=None, app_data=None, user_data=None) -> None:
        """The Copy button: put the whole reply on the clipboard."""
        dpg.set_clipboard_text(self._copy_text)

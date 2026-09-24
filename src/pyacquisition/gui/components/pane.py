"""The pieces that the panes on the left of the window share: a frame with nothing
behind it, cards one pixel apart, and thin lines across the pane."""

import dearpygui.dearpygui as dpg

from ..constants import page_width

CARD_SPACING = 1  # between one card and the next


def fit_to_page(window) -> None:
    """
    Make a window as wide as a page: the left part of the viewport, beside the menu. A
    window that is not shown in a viewport, such as in a test, is left as it is.

    Args:
        window: The window.
    """
    try:
        width = dpg.get_viewport_client_width()
    except Exception:
        return
    dpg.configure_item(window, width=page_width(width))


def frame_theme():
    """
    A theme for the frame of a pane: no background, so that the pane is only what is
    in it, and cards that are one pixel apart, with the header as far from the first as
    they are from each other.
    """
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(
                dpg.mvThemeCol_ChildBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core
            )
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(
                dpg.mvStyleVar_ItemSpacing,
                6,
                CARD_SPACING,
                category=dpg.mvThemeCat_Core,
            )
    return theme


def add_rule(parent, width: int, rules: list) -> None:
    """
    Add a line across a pane, like the one under its header.

    Args:
        parent: The item to put it in.
        width (int): How wide it is.
        rules (list): Where to keep it, as a `(drawlist, line)`, with the others.
    """
    drawlist = dpg.add_drawlist(width=width, height=1, parent=parent)
    line = dpg.draw_line((0, 0), (width, 0), thickness=1, parent=drawlist)
    rules.append((drawlist, line))


def fit_rules(rules: list, width: int) -> None:
    """Make the lines a width, if they are not already."""
    for drawlist, line in rules:
        if dpg.get_item_configuration(drawlist)["width"] != width:
            dpg.configure_item(drawlist, width=width)
            dpg.configure_item(line, p2=(width, 0))


def color_rules(rules: list, color) -> None:
    """Draw the lines in a colour."""
    for _, line in rules:
        dpg.configure_item(line, color=color)

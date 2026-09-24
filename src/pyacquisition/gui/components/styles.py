import dearpygui.dearpygui as dpg

from ..constants import STATE_STYLES

# A card is tinted, and given a coloured border, by its state. The headers use the
# same colours.
CARD_STYLES = {name: style for name, style in STATE_STYLES.items() if name != "neutral"}


def arrow_theme():
    """
    A theme for the arrows that move a queued task: a white arrowhead with no button
    behind it. An arrow that cannot be used is drawn dark and faint, so that it is
    clear which way a task can go.
    """
    clear = (0, 0, 0, 0)
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            for column, colour in (
                (dpg.mvThemeCol_Button, clear),
                (dpg.mvThemeCol_ButtonHovered, (255, 255, 255, 40)),
                (dpg.mvThemeCol_ButtonActive, (255, 255, 255, 80)),
                (dpg.mvThemeCol_Text, (255, 255, 255)),
            ):
                dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Core)
        with dpg.theme_component(dpg.mvButton, enabled_state=False):
            dpg.add_theme_color(
                dpg.mvThemeCol_Button, clear, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_Text, (78, 78, 78), category=dpg.mvThemeCat_Core
            )
    return theme


def primary_button_theme():
    """A blue theme for the button that does the main thing in a window."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            for column, colour in (
                (dpg.mvThemeCol_Button, (36, 92, 158)),
                (dpg.mvThemeCol_ButtonHovered, (52, 120, 200)),
                (dpg.mvThemeCol_ButtonActive, (70, 140, 225)),
            ):
                dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(
                dpg.mvStyleVar_FrameRounding, 3, category=dpg.mvThemeCat_Core
            )
    return theme


def frame_themes() -> dict:
    """
    One theme for each state of a frame: a child window with no background and no
    padding, outlined in the colour of the state. Unlike a card it is not tinted, so
    what is inside shows on the background of the window, and a header inside it
    can share the outline.

    A theme reaches the child windows inside a frame too, so a window that wants
    padding, or a background, needs a theme of its own, such as `padded_theme`.

    Returns:
        dict: The theme of each state, by its name: `running`, `paused`, `aborting`
        and `idle`.
    """
    themes = {}
    for name, style in CARD_STYLES.items():
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_color(
                    dpg.mvThemeCol_ChildBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Border, style["border"], category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_ChildBorderSize,
                    style["width"],
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_WindowPadding, 0, 0, category=dpg.mvThemeCat_Core
                )
        themes[name] = theme
    return themes


def padded_theme(x: int, y: int):
    """
    A theme that gives a child window padding, for one inside a frame, which has none.

    The window must be made with `border=True`, because a child window without a
    border has no padding, whatever it is given. Nor does one whose border is no
    thick, so the theme gives it a border of one pixel, which it makes clear.

    Args:
        x (int): The space at the left and right, in pixels.
        y (int): The space at the top and bottom, in pixels.
    """
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_style(
                dpg.mvStyleVar_WindowPadding, x, y, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_ChildBorderSize, 1, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_Border, (0, 0, 0, 0), category=dpg.mvThemeCat_Core
            )
    return theme


def compact_theme(spacing: int = 1, padding: int = 1):
    """
    A theme that packs what is in a container close: the lines of text are only
    `spacing` pixels apart, where they are usually four, and buttons are not as tall.
    The cells of a table have no padding, so that a coloured cell fills its row.

    Args:
        spacing (int): The space between items one above the other, in pixels.
        padding (int): The space above and below the label of a button, in pixels.
    """
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(
                dpg.mvStyleVar_ItemSpacing, 6, spacing, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_CellPadding, 0, 0, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_FramePadding, 4, padding, category=dpg.mvThemeCat_Core
            )
    return theme


def card_themes() -> dict:
    """
    One theme for each look of a card: a child window with a tinted background and
    a coloured border, for `running`, `paused`, `aborting` and `idle`.

    Returns:
        dict: The theme of each style, by its name.
    """
    themes = {}
    for name, style in CARD_STYLES.items():
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_color(
                    dpg.mvThemeCol_ChildBg,
                    style["background"],
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Border,
                    style["border"],
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_ChildBorderSize,
                    style["width"],
                    category=dpg.mvThemeCat_Core,
                )
        themes[name] = theme
    return themes

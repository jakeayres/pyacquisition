import dearpygui.dearpygui as dpg

from ..constants import STATE_STYLES

# A card is tinted, and given a coloured border, by its state. The headers use the
# same colours.
CARD_STYLES = {name: style for name, style in STATE_STYLES.items() if name != "neutral"}


def arrow_theme():
    """
    A theme for the arrows that move a queued task. An arrow that cannot be used is
    drawn dark and faint, so that it is clear which way a task can go.
    """
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton, enabled_state=False):
            dpg.add_theme_color(
                dpg.mvThemeCol_Button, (26, 26, 26), category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_Text, (78, 78, 78), category=dpg.mvThemeCat_Core
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

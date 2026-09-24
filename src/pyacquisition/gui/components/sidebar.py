import webbrowser

import dearpygui.dearpygui as dpg

from ..constants import SIDEBAR_WIDTH
from .fonts import UI_BOLD_FONTS, UI_FONTS, add_font

# A dark panel like the pages beside it, but a little brighter and bluer than they are,
# with a thin edge along its right side, so that it reads as a menu and not as content.
BACKGROUND = (24, 27, 35)
EDGE = (46, 52, 66)
TEXT = (226, 229, 236)
MUTED_TEXT = (140, 146, 160)
SELECTED = (38, 45, 60)  # the tab of the page that is shown
HOVERED = (31, 36, 47)
CLICKED = (46, 55, 74)
DIVIDER = (42, 47, 60)
LINK = (110, 165, 240)
TITLE = "MyDashboard"  # a placeholder for the name of the dashboard
DOCS_URL = "https://pyacquisition.readthedocs.io"
LINK_LABEL = "Built with PyAcquisition"

WIDTH = SIDEBAR_WIDTH
TAB_HEIGHT = 36
PADDING = (12, 14)  # the space at the sides and at the top and bottom
FONT_SIZE = 17
TITLE_FONT_SIZE = 22
TEXT_INDENT = 2  # spaces before the name of a tab


class Sidebar:
    """
    The menu down the left of the window: a dark panel, a little brighter than the pages,
    with light text, that holds a
    tab for each page. Clicking a tab shows its page, in the rest of the window, and the
    tab of the page that is shown is lit. The title is at the top and a link to the docs
    is at the very bottom.

    The pages are shown by whoever owns the menu: `on_select` is called with the name
    of the page when its tab is clicked.
    """

    def __init__(self, pages=(), on_select=None, title: str = TITLE) -> None:
        """
        Args:
            pages: The names of the pages, in the order of their tabs. The first is
                shown to start with.
            on_select: Called with the name of a page when its tab is clicked.
            title (str): The name at the top of the menu.
        """
        self.pages = list(pages)
        self.on_select = on_select
        self.selected = self.pages[0] if self.pages else None
        self.tabs = {}  # the tab of each page
        self.window_tag = dpg.generate_uuid()
        # The fonts have to be loaded before the window is first shown.
        self._font = add_font(FONT_SIZE, UI_FONTS)
        self._title_font = add_font(TITLE_FONT_SIZE, UI_BOLD_FONTS)

        with dpg.window(
            label="Menu",
            pos=[0, 0],
            width=WIDTH,
            height=600,
            no_title_bar=True,
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            tag=self.window_tag,
        ):
            self.title_tag = dpg.add_text(title)
            dpg.add_separator()
            for page in self.pages:
                self.tabs[page] = dpg.add_selectable(
                    label=" " * TEXT_INDENT + page,
                    height=TAB_HEIGHT,
                    callback=self._clicked,
                    user_data=page,
                )
            self.spacer_tag = dpg.add_spacer(height=100)
            dpg.add_separator()
            self.link_tag = dpg.add_selectable(
                label=LINK_LABEL,
                height=TAB_HEIGHT - 6,
                callback=self._open_docs,
                user_data=DOCS_URL,
            )
            dpg.bind_item_theme(self.link_tag, self._make_link_theme())
        self._theme = self._make_theme()
        dpg.bind_item_theme(self.window_tag, self._theme)
        if self._font is not None:
            dpg.bind_item_font(self.window_tag, self._font)
        dpg.bind_item_font(self.title_tag, self._title_font or self._font or 0)
        self._show()

    @staticmethod
    def _make_link_theme():
        """The link at the foot of the menu: blue, and not light like the tabs."""
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvSelectable):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Text, LINK, category=dpg.mvThemeCat_Core
                )
        return theme

    @staticmethod
    def _make_theme():
        """The dark panel, the light text on it, and the tabs."""
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                for column, colour in (
                    (dpg.mvThemeCol_WindowBg, BACKGROUND),
                    (dpg.mvThemeCol_Text, TEXT),
                    (dpg.mvThemeCol_TextDisabled, MUTED_TEXT),
                    (dpg.mvThemeCol_Border, EDGE),
                    (dpg.mvThemeCol_Separator, DIVIDER),
                    (dpg.mvThemeCol_Header, SELECTED),
                    (dpg.mvThemeCol_HeaderHovered, HOVERED),
                    (dpg.mvThemeCol_HeaderActive, CLICKED),
                ):
                    dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Core)
                for style, values in (
                    (dpg.mvStyleVar_WindowPadding, PADDING),
                    (dpg.mvStyleVar_WindowRounding, (0,)),
                    (dpg.mvStyleVar_WindowBorderSize, (1,)),
                    (dpg.mvStyleVar_FrameRounding, (8,)),
                    (dpg.mvStyleVar_ItemSpacing, (6, 4)),
                    (dpg.mvStyleVar_SelectableTextAlign, (0, 0.5)),
                ):
                    dpg.add_theme_style(style, *values, category=dpg.mvThemeCat_Core)
        return theme

    def select(self, page: str, notify: bool = True) -> None:
        """
        Light the tab of a page, and show the page.

        Args:
            page (str): The name of the page.
            notify (bool): Whether to call `on_select`.

        Raises:
            ValueError: If there is no such page.
        """
        if page not in self.tabs:
            raise ValueError(f"page must be one of {', '.join(self.pages)}, got {page!r}")
        self.selected = page
        self._show()
        if notify and self.on_select:
            self.on_select(page)

    def _show(self) -> None:
        """Light the tab of the page that is shown, and no other."""
        for page, tab in self.tabs.items():
            dpg.set_value(tab, page == self.selected)

    def _clicked(self, sender, app_data, page: str) -> None:
        """A tab was clicked. It stays lit if it was the page that was shown."""
        self.select(page)

    @staticmethod
    def _open_docs(sender, app_data, url: str) -> None:
        """The link at the foot of the menu was clicked: open the docs in a browser."""
        dpg.set_value(sender, False)  # it is a link, and is not a choice
        webbrowser.open(url)

    def tick(self) -> None:
        """
        Call this often, such as once a frame. It keeps the menu as tall as the window,
        with the link at the very bottom of it.
        """
        height = dpg.get_viewport_client_height()
        if height < 200 or dpg.get_item_configuration(self.window_tag)["height"] == height:
            return
        dpg.configure_item(self.window_tag, height=height)
        # What is between the tabs and the link takes up the rest of the height.
        used = 2 * PADDING[1] + 40 + len(self.pages) * (TAB_HEIGHT + 4) + TAB_HEIGHT + 40
        dpg.configure_item(self.spacer_tag, height=max(height - used, 0))

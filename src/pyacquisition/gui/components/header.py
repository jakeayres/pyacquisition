import dearpygui.dearpygui as dpg

from ..constants import STATE_STYLES, WHITE

CAPTION_COLOR = (150, 170, 200)
SUBTITLE_COLOR = (190, 190, 190)
BADGE_TEXT_COLOR = (10, 10, 10)

# The default font is a small pixel font, 7 pixels a character and 13 high. It is
# only sharp at that size and on whole pixels, so everything in a header is drawn at
# it, and at whole-pixel positions. Hierarchy comes from colour and layout instead.
CHAR_WIDTH = 7
TEXT_HEIGHT = 13


def text_width(text: str) -> int:
    """
    How wide text is in the default font, in pixels.

    Args:
        text (str): The text.
    """
    return CHAR_WIDTH * len(text)


def fit(text: str, max_width: int) -> str:
    """
    Shorten text with `...` so that it fits in a width. It is unchanged if it fits.

    Args:
        text (str): The text.
        max_width (int): The width available, in pixels.
    """
    if text_width(text) <= max_width:
        return text
    keep = int(max_width // CHAR_WIDTH) - 3
    return text[:keep] + "..." if keep > 0 else ""


class PaneHeader:
    """
    The header of a pane: a coloured strip with a title, and optionally a caption
    above it, a subtitle beside it and a status badge at the right.

    The colours come from a style: `running`, `paused`, `aborting`, `idle` or
    `neutral`. They are the ones the task cards use, so a pane's header and its
    card agree.

    A header that is `collapsible` has a chevron, and clicking anywhere on the strip
    collapses or expands the pane. That calls `on_collapse` with whether the pane is
    now collapsed, and it is up to the pane to hide what is below the header.

    The click is handled by the strip itself, not by a button on top of it. A drawing
    takes the mouse for itself, so a button placed over it could never be clicked.
    """

    HEIGHT = 30
    HEIGHT_WITH_CAPTION = 44
    BADGE_HEIGHT = 20

    def __init__(
        self,
        parent,
        width: int,
        title: str = "",
        subtitle: str = "",
        caption: str | None = None,
        badge: str | None = None,
        style: str = "neutral",
        collapsible: bool = False,
        on_collapse=None,
    ) -> None:
        """
        Args:
            parent: The item to put the header in.
            width (int): The width of the header in pixels.
            title (str): The main text.
            subtitle (str): Smaller text beside the title.
            caption (str | None): Small text above the title, such as `DATA FILE`.
                A header with a caption is taller.
            badge (str | None): Text for a coloured pill at the right, such as
                `RUNNING`.
            style (str): The colours to use.
            collapsible (bool): Whether clicking the header collapses the pane. It
                is shown by a chevron.
            on_collapse: Called with whether the pane is now collapsed.
        """
        self.width = width
        self.height = self.HEIGHT_WITH_CAPTION if caption is not None else self.HEIGHT
        self.collapsible = collapsible
        self.on_collapse = on_collapse
        self.collapsed = False

        self.title = title
        self.subtitle = subtitle
        self.caption = caption
        self.badge = badge
        self.style = style

        with dpg.theme() as no_padding:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_style(
                    dpg.mvStyleVar_WindowPadding, 0, 0, category=dpg.mvThemeCat_Core
                )
        self.container = dpg.add_child_window(
            parent=parent,
            width=width,
            height=self.height,
            border=False,
            no_scrollbar=True,
        )
        dpg.bind_item_theme(self.container, no_padding)

        self.drawlist = dpg.add_drawlist(
            width=width, height=self.height, parent=self.container
        )
        self._background = dpg.draw_rectangle(
            (0, 0), (width, self.height), parent=self.drawlist
        )
        self._accent = dpg.draw_rectangle(
            (0, 0), (5, self.height), parent=self.drawlist
        )
        self._caption = dpg.draw_text(
            (0, 0), "", size=TEXT_HEIGHT, color=CAPTION_COLOR, parent=self.drawlist
        )
        self._title = dpg.draw_text(
            (0, 0), "", size=TEXT_HEIGHT, color=WHITE, parent=self.drawlist
        )
        self._subtitle = dpg.draw_text(
            (0, 0), "", size=TEXT_HEIGHT, color=SUBTITLE_COLOR, parent=self.drawlist
        )
        self._badge_rect = dpg.draw_rectangle(
            (0, 0), (0, 0), rounding=8, parent=self.drawlist
        )
        self._badge_text = dpg.draw_text(
            (0, 0), "", size=TEXT_HEIGHT, color=BADGE_TEXT_COLOR, parent=self.drawlist
        )

        self._chevron = None
        self._handlers = None
        if collapsible:
            self._chevron = dpg.draw_triangle(
                (0, 0), (0, 0), (0, 0), color=WHITE, fill=WHITE, parent=self.drawlist
            )
            with dpg.item_handler_registry() as self._handlers:
                dpg.add_item_clicked_handler(
                    button=dpg.mvMouseButton_Left, callback=self._toggle
                )
            dpg.bind_item_handler_registry(self.drawlist, self._handlers)

        self._layout()

    def update(
        self,
        title: str,
        subtitle: str = "",
        badge: str | None = None,
        style: str = "neutral",
        caption: str | None = None,
    ) -> None:
        """
        Show new text and colours. Anything not given goes back to its default, so
        pass everything that should show.

        Args:
            title (str): The main text.
            subtitle (str): Smaller text beside the title.
            badge (str | None): Text for the pill at the right, or `None` for none.
            style (str): The colours to use.
            caption (str | None): Small text above the title. It only shows if the
                header was made with a caption, because that makes it taller.
        """
        self.title, self.subtitle, self.badge, self.style = (
            title,
            subtitle,
            badge,
            style,
        )
        if self.caption is not None:
            self.caption = caption if caption is not None else self.caption
        self._layout()

    def resize(self, width: int) -> None:
        """
        Make the header a different width, for example when a scroll bar appears.

        Args:
            width (int): The new width in pixels.
        """
        self.width = width
        dpg.configure_item(self.container, width=width)
        dpg.configure_item(self.drawlist, width=width)
        self._layout()

    def fit_to(self, window) -> None:
        """
        Make the header the width of the space in a window, allowing for its scroll
        bar, so that it never makes the window scroll sideways.

        Args:
            window: The window that holds the header.
        """
        width = dpg.get_item_configuration(window)["width"] - 16  # window padding
        if dpg.get_y_scroll_max(window) > 0:
            width -= 14  # the scroll bar
        if width > 60 and width != self.width:
            self.resize(width)

    def _toggle(self, sender=None, app_data=None, user_data=None) -> None:
        """The header was clicked."""
        self.collapsed = not self.collapsed
        self._layout()
        if self.on_collapse:
            self.on_collapse(self.collapsed)

    def _layout(self) -> None:
        """Place and colour everything, for the current text and width."""
        width, height = self.width, self.height
        colours = STATE_STYLES[self.style]
        accent, tint = colours["border"], colours["background"]

        dpg.configure_item(
            self._background, pmax=(width, height), color=tint, fill=tint
        )
        dpg.configure_item(self._accent, pmax=(5, height), color=accent, fill=accent)

        left = 36 if self.collapsible else 16
        right = width - 10

        if self._chevron is not None:
            # Pointing down while the pane is open, and right when it is collapsed.
            y = height // 2
            if self.collapsed:
                points = ((16, y - 5), (16, y + 5), (22, y))
            else:
                points = ((14, y - 3), (24, y - 3), (19, y + 3))
            dpg.configure_item(self._chevron, p1=points[0], p2=points[1], p3=points[2])

        if self.badge:
            badge_width = text_width(self.badge) + 18
            x = width - badge_width - 10
            y = (height - self.BADGE_HEIGHT) // 2
            dpg.configure_item(
                self._badge_rect,
                pmin=(x, y),
                pmax=(x + badge_width, y + self.BADGE_HEIGHT),
                color=accent,
                fill=accent,
                show=True,
            )
            dpg.configure_item(
                self._badge_text, pos=(x + 9, y + 3), text=self.badge, show=True
            )
            right = x - 12
        else:
            dpg.configure_item(self._badge_rect, show=False)
            dpg.configure_item(self._badge_text, show=False)

        if self.caption is not None:
            # Two lines: the caption above the title.
            caption_y, title_y = 7, 24
            dpg.configure_item(
                self._caption, pos=(left, caption_y), text=self.caption, show=True
            )
        else:
            title_y = (height - TEXT_HEIGHT) // 2
            dpg.configure_item(self._caption, show=False)

        title = fit(self.title, right - left)
        dpg.configure_item(self._title, pos=(left, title_y), text=title)

        subtitle_left = left + text_width(title) + 14
        subtitle = fit(self.subtitle, right - subtitle_left) if self.subtitle else ""
        dpg.configure_item(
            self._subtitle,
            pos=(subtitle_left, title_y),
            text=subtitle,
            show=bool(subtitle),
        )

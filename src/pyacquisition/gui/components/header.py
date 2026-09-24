import dearpygui.dearpygui as dpg

from ..constants import STATE_STYLES, WHITE

CAPTION_COLOR = (150, 170, 200)
SUBTITLE_COLOR = (190, 190, 190)
BADGE_TEXT_COLOR = (10, 10, 10)
ACTION_WIDTH = 34  # the space at the right that the play or pause icon takes

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


def fit_start(text: str, max_width: int) -> str:
    """
    Shorten text with `...` at its start so that it fits in a width, keeping its end,
    which is what tells one path from another. It is unchanged if it fits.

    Args:
        text (str): The text.
        max_width (int): The width available, in pixels.
    """
    if text_width(text) <= max_width:
        return text
    keep = int(max_width // CHAR_WIDTH) - 3
    return "..." + text[-keep:] if keep > 0 else ""


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
        flat: bool = False,
        title_font=None,
        title_size: int = TEXT_HEIGHT,
        on_action=None,
        action: str = "pause",
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
            flat (bool): Draw no tinted background, but a line along the bottom in
                the colour of the state. For a header inside a frame that is coloured
                by the same state, which it is then a part of. It has no bar at its
                left either.
            title_font: A font for the title, which is then larger, or `None` for
                the default font. The default font is only sharp at its own size.
            title_size (int): The height of the text of `title_font`, in pixels, for
                placing it.
            on_action: If given, the header has a play or pause icon at its right, and
                this is called, with no arguments, when it is clicked.
            action (str): Which icon it starts with: `pause`, two bars, for something
                that is running, or `play`, a triangle, for something that is paused.
        """
        self.flat = flat
        self.title_font = title_font
        self.title_size = title_size
        self.on_action = on_action
        self.action = action
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
                if flat:  # nothing behind it, so it is as clear as the pane
                    dpg.add_theme_color(
                        dpg.mvThemeCol_ChildBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core
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
        self._rule = dpg.draw_line(
            (0, 0), (0, 0), thickness=1, show=flat, parent=self.drawlist
        )
        self._caption = dpg.draw_text(
            (0, 0), "", size=TEXT_HEIGHT, color=CAPTION_COLOR, parent=self.drawlist
        )
        self._title = dpg.draw_text(
            (0, 0), "", size=TEXT_HEIGHT, color=WHITE, parent=self.drawlist
        )
        self._title_item = None
        if title_font is not None:
            # A drawing cannot take a font, so the title is a text on top of it.
            self._title_item = dpg.add_text("", color=WHITE, parent=self.container)
            dpg.bind_item_font(self._title_item, title_font)
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
        # The icon is a triangle for play and two bars for pause, of which only one
        # kind is shown.
        self._play = dpg.draw_triangle(
            (0, 0), (0, 0), (0, 0), color=WHITE, fill=WHITE, show=False, parent=self.drawlist
        )
        self._bars = [
            dpg.draw_rectangle(
                (0, 0), (0, 0), color=WHITE, fill=WHITE, show=False, parent=self.drawlist
            )
            for _ in range(2)
        ]
        if collapsible or on_action is not None:
            with dpg.item_handler_registry() as self._handlers:
                dpg.add_item_clicked_handler(
                    button=dpg.mvMouseButton_Left, callback=self._clicked
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

    def fit_to(self, window, inset: int = 0) -> None:
        """
        Make the header the width of the space in a window, allowing for its scroll
        bar, so that it never makes the window scroll sideways.

        Args:
            window: The window that holds the header.
            inset (int): How much narrower the header is than the window's own space,
                because it is in a frame with a border, for example.
        """
        width = (
            dpg.get_item_configuration(window)["width"] - 16 - inset
        )  # window padding
        if dpg.get_y_scroll_max(window) > 0:
            width -= 14  # the scroll bar
        if width > 60 and width != self.width:
            self.resize(width)

    def set_action(self, action: str) -> None:
        """
        Show the play or pause icon.

        Args:
            action (str): `pause` or `play`.
        """
        self.action = action
        self._layout()

    def _clicked(self, sender=None, app_data=None, user_data=None) -> None:
        """The header was clicked: on the icon, if it has one, or anywhere else."""
        if self.on_action is not None:
            x, _ = dpg.get_drawing_mouse_pos()
            if x >= self.width - ACTION_WIDTH:
                self.on_action()
                return
        if self.collapsible:
            self._toggle()

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

        if self.flat:
            clear = (0, 0, 0, 0)
            dpg.configure_item(
                self._background, pmax=(width, height), color=clear, fill=clear
            )
            dpg.configure_item(
                self._rule, p1=(0, height - 1), p2=(width, height - 1), color=accent
            )
        else:
            dpg.configure_item(
                self._background, pmax=(width, height), color=tint, fill=tint
            )
        dpg.configure_item(
            self._accent,
            pmax=(5, height),
            color=accent,
            fill=accent,
            show=not self.flat,
        )

        left = 36 if self.collapsible else 16
        right = width - 10

        playing = self.action == "play"
        if self.on_action is not None:
            # Two bars if it is running, and a triangle if it is paused.
            x, y = width - ACTION_WIDTH + 10, height // 2
            dpg.configure_item(
                self._play,
                p1=(x, y - 7),
                p2=(x, y + 7),
                p3=(x + 12, y),
                show=playing,
            )
            for i, bar in enumerate(self._bars):
                dpg.configure_item(
                    bar,
                    pmin=(x + i * 8, y - 7),
                    pmax=(x + i * 8 + 4, y + 7),
                    show=not playing,
                )
            right = width - ACTION_WIDTH

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
            x = right - badge_width
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
        if self._title_item is not None:
            dpg.set_value(self._title_item, title)
            dpg.set_item_pos(
                self._title_item, (left, (height - self.title_size) // 2)
            )
            dpg.configure_item(self._title, show=False)
        else:
            dpg.configure_item(self._title, pos=(left, title_y), text=title)

        title_width = text_width(title)
        if self._title_item is not None:
            # The font is monospace, and a character of it is a little over half as
            # wide as the text is high.
            title_width = round(len(title) * self.title_size * 0.6)
        subtitle_left = left + title_width + 14
        if self._title_item is not None:
            title_y = (height - TEXT_HEIGHT) // 2  # level with the middle of the title
        subtitle = fit(self.subtitle, right - subtitle_left) if self.subtitle else ""
        dpg.configure_item(
            self._subtitle,
            pos=(subtitle_left, title_y),
            text=subtitle,
            show=bool(subtitle),
        )

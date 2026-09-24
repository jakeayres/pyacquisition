WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


TEXT_COLOR = (200, 200, 200)
EMPHASIS_COLOR = (255, 171, 91)
SECONDARY_COLOR = (128, 196, 233)
MUTED_COLOR = (130, 130, 130)
OK_COLOR = (110, 225, 150)
ERROR_COLOR = (245, 115, 115)


# The colours that the values of the Live Data window take in turn, one for each
# measurement. They are bright, so that they read on a dark card of any state.
VALUE_COLORS = (
    (110, 200, 240),  # blue
    (255, 190, 90),  # amber
    (240, 130, 180),  # pink
    (170, 230, 120),  # green
    (180, 150, 255),  # lilac
    (100, 225, 205),  # teal
    (255, 135, 110),  # coral
    (225, 225, 120),  # yellow
)

# The menu down the far left, which changes the page that is shown beside it.
SIDEBAR_WIDTH = 253
# The pages are in the left part of the window, beside the menu, and the plot fills the
# rest: the pages and the menu together are five twelfths of the window, and the plot
# is the other seven twelfths. Where a page starts, and how far down.
PANE_X = SIDEBAR_WIDTH + 20
TOP_Y = 20
# The height of the data file pane, and so where the live data pane starts under it.
FILE_PANE_HEIGHT = 292


def plot_x(viewport_width: int) -> int:
    """Where the plot starts: it fills the right seven twelfths of the window."""
    return viewport_width * 5 // 12


MINIMUM_PAGE_WIDTH = 360


def page_width(viewport_width: int) -> int:
    """
    How wide a page is that fills the left part of the window, beside the menu. It is
    never narrower than the least that the controls on a page are laid out for.

    Args:
        viewport_width (int): The width of the window.
    """
    return max(plot_x(viewport_width) - PANE_X - 10, MINIMUM_PAGE_WIDTH)


# What a window is made as wide as until it is laid out, for a window 1920 pixels wide.
DEFAULT_PAGE_WIDTH = page_width(1920)


# The colours of a task manager's card and header, by state. They are shared, so
# that a pane's header and its card agree.
STATE_STYLES = {
    "running": {"background": (14, 50, 34), "border": (70, 200, 125), "width": 2},
    "paused": {"background": (58, 44, 12), "border": (240, 175, 50), "width": 2},
    "aborting": {"background": (62, 20, 20), "border": (220, 70, 70), "width": 2},
    "idle": {"background": (26, 26, 26), "border": (100, 100, 100), "width": 1},
    "neutral": {"background": (28, 34, 44), "border": (91, 171, 255), "width": 1},
}

# A task waiting in a queue is a blue card with a bold edge at its left, like the
# header of the data file pane.
QUEUED_BACKGROUND = STATE_STYLES["neutral"]["background"]
QUEUED_ACCENT = STATE_STYLES["neutral"]["border"]

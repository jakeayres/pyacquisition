WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


TEXT_COLOR = (200, 200, 200)
EMPHASIS_COLOR = (255, 171, 91)
SECONDARY_COLOR = (128, 196, 233)


# The colours of a task manager's card and header, by state. They are shared, so
# that a pane's header and its card agree.
STATE_STYLES = {
    "running": {"background": (14, 50, 34), "border": (70, 200, 125), "width": 2},
    "paused": {"background": (58, 44, 12), "border": (240, 175, 50), "width": 2},
    "aborting": {"background": (62, 20, 20), "border": (220, 70, 70), "width": 2},
    "idle": {"background": (26, 26, 26), "border": (100, 100, 100), "width": 1},
    "neutral": {"background": (28, 34, 44), "border": (91, 171, 255), "width": 1},
}

import os

import dearpygui.dearpygui as dpg

from ...core.logging import logger

# The default font is a small pixel font that is only sharp at its own size, so text
# that is larger is set in a real font. A monospace one, so that a value does not
# shift about as its digits change. It is the first of these that is installed.
_WINDOWS = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
MONOSPACE_FONTS = (
    os.path.join(_WINDOWS, "consola.ttf"),
    os.path.join(_WINDOWS, "lucon.ttf"),
    os.path.join(_WINDOWS, "cour.ttf"),
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/Library/Fonts/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/liberation-mono/LiberationMono-Regular.ttf",
)

# The fonts of the menu, which are not monospace and not pixels: the font of the
# system, or one that looks like it, in regular and in bold.
UI_FONTS = (
    os.path.join(_WINDOWS, "segoeui.ttf"),
    os.path.join(_WINDOWS, "arial.ttf"),
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)
UI_BOLD_FONTS = (
    os.path.join(_WINDOWS, "segoeuib.ttf"),
    os.path.join(_WINDOWS, "arialbd.ttf"),
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)


def find_font(candidates=MONOSPACE_FONTS) -> str | None:
    """
    The first of the fonts that is installed.

    Args:
        candidates: Paths of fonts, best first.

    Returns:
        str | None: Its path, or `None` if none of them is.
    """
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def add_font(size: int, candidates=MONOSPACE_FONTS) -> int | None:
    """
    Load a font at a size, for `dpg.bind_item_font`. It is a monospace font unless
    other `candidates` are given.

    A font has to be loaded before the window is first shown, so call this while the
    interface is being set up.

    Args:
        size (int): The height of the text, in pixels.
        candidates: Paths of fonts to try, best first.

    Returns:
        int | None: The font, or `None` if there is no font to load. Text that is not
        given a font is drawn in the default font, so the interface still works.
    """
    path = find_font(candidates)
    if path is None:
        logger.warning("[GUI] No font found, so large text is not larger")
        return None
    try:
        with dpg.font_registry():
            return dpg.add_font(path, size)
    except Exception as e:  # a font file that cannot be read
        logger.warning(f"[GUI] Could not load the font {path}: {e}")
        return None

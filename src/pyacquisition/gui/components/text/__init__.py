import dearpygui.dearpygui as dpg


def add_header(text: str, **kwargs) -> None:
    """
    Add a header to the GUI.

    Args:
        text (str): The text for the header.
        parent (str, optional): The parent item to attach the header to. Defaults to None.
    """
    dpg.add_spacer(height=5)
    element = dpg.add_text(text, **kwargs)
    dpg.add_spacer(height=5)
    return element


def add_text(text: str, **kwargs) -> None:
    """
    Add a text label to the GUI.

    Args:
        text (str): The text.
        parent (str, optional): The parent item to attach the text to. Defaults to None.
    """
    dpg.add_spacer(height=5)
    element = dpg.add_text(
        text,
        indent=10,
        color=(200, 200, 200),
        **kwargs,
    )
    dpg.add_spacer(height=5)
    return element


def add_text_area(**kwargs):
    """
    Create a text area for displaying responses.

    Returns:
        str: The UUID of the created text area.
    """
    dpg.add_spacer(height=5)
    area = dpg.add_input_text(
        multiline=True,
        readonly=True,
        indent=10,
        **kwargs,
    )
    dpg.add_spacer(height=5)
    return area

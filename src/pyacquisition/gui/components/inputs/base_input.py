import dearpygui.dearpygui as dpg


class BaseInput:
    """
    Base class for input components.

    An input has no label of its own on screen: the group that holds it puts the
    label beside it. `label` is the name of the parameter it sets.
    """

    def __init__(self, label: str, default_value=None) -> None:
        self.label = label
        self.default_value = default_value
        self.uuid = dpg.generate_uuid()
        self.hint = ""  # what to tell the user about it, in a tooltip

    def _options(self, parent: str | None, width: int) -> dict:
        """
        The options every kind of input is drawn with.

        Never give a box you type into `on_enter=True`. It makes the box keep what
        you type only when Enter is pressed, and put back the old value if you click
        anywhere else, such as a Send button. The request is then sent with the value
        that was there before you typed.
        """
        options = dict(default_value=self.default_value, tag=self.uuid, width=width)
        if parent is not None:
            options["parent"] = parent
        return options

    def draw(self, parent: str | None = None, width: int = -1) -> None:
        """Draw the input component, optionally on the specified parent."""
        return dpg.add_input_text(**self._options(parent, width))

    def reset(self) -> None:
        """Reset the input component to its default value."""
        dpg.set_value(self.uuid, self.default_value)

    def get_value(self) -> any:
        """Retrieve the current value of the input."""
        return dpg.get_value(self.uuid)

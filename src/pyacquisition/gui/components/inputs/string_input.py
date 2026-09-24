from .base_input import BaseInput


class StringInput(BaseInput):
    """String input component."""

    def __init__(self, label: str, default_value: str = "") -> None:
        super().__init__(label, default_value)

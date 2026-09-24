import dearpygui.dearpygui as dpg

HEIGHT = 40
BACKGROUND = (18, 20, 26)  # a blank card, darker than one that holds something
HOVERED_BACKGROUND = (28, 32, 42)
CIRCLE = (255, 255, 255, 235)  # white
HOVERED_CIRCLE = (255, 255, 255, 255)
CROSS = (18, 20, 26)  # a dark cross inside it
CIRCLE_RADIUS = 11
CROSS_SIZE = 5  # from the middle of the cross to the end of each arm
CROSS_THICKNESS = 2


class AddCard:
    """
    A blank card with a dark cross inside a white circle in the middle, that is a button:
    it lights up under the mouse, and `on_click` is called, with no arguments, when it is clicked. It is for
    adding something to a list, such as a task to a queue.

    It is a single drawing, so the whole card is what is clicked. Call `tick` each
    frame for it to light up.
    """

    def __init__(
        self,
        parent,
        width: int,
        on_click=None,
        height: int = HEIGHT,
        before=0,
    ) -> None:
        """
        Args:
            parent: The item to put the card in.
            width (int): The width of the card in pixels.
            on_click: Called, with no arguments, when the card is clicked.
            height (int): The height of the card in pixels.
            before: The item in the parent to put it in front of. It goes last if there
                is none.
        """
        self.width = width
        self.height = height
        self.on_click = on_click
        self.hovered = False

        self.drawlist = dpg.add_drawlist(
            width=width, height=height, parent=parent, before=before
        )
        self._background = dpg.draw_rectangle(
            (0, 0),
            (width, height),
            color=BACKGROUND,
            fill=BACKGROUND,
            parent=self.drawlist,
        )
        self._circle = dpg.draw_circle(
            (0, 0),
            CIRCLE_RADIUS,
            color=CIRCLE,
            fill=CIRCLE,
            parent=self.drawlist,
        )
        self._arms = [
            dpg.draw_line(
                (0, 0),
                (0, 0),
                color=CROSS,
                thickness=CROSS_THICKNESS,
                parent=self.drawlist,
            )
            for _ in range(2)
        ]
        with dpg.item_handler_registry() as handlers:
            dpg.add_item_clicked_handler(
                button=dpg.mvMouseButton_Left, callback=self._clicked
            )
        dpg.bind_item_handler_registry(self.drawlist, handlers)
        self._layout()

    def resize(self, width: int) -> None:
        """Make the card a different width, for example when a scroll bar appears."""
        self.width = width
        dpg.configure_item(self.drawlist, width=width)
        dpg.configure_item(self._background, pmax=(width, self.height))
        self._layout()

    def tick(self) -> None:
        """Call this each frame: the card is lit while the mouse is over it."""
        hovered = dpg.is_item_hovered(self.drawlist)
        if hovered == self.hovered:
            return
        self.hovered = hovered
        background = HOVERED_BACKGROUND if hovered else BACKGROUND
        circle = HOVERED_CIRCLE if hovered else CIRCLE
        dpg.configure_item(self._background, color=background, fill=background)
        dpg.configure_item(self._circle, color=circle, fill=circle)

    def _layout(self) -> None:
        """Put the circle, and the cross in it, in the middle."""
        x, y, s = self.width / 2, self.height / 2, CROSS_SIZE
        dpg.configure_item(self._circle, center=(x, y))
        horizontal, vertical = self._arms
        dpg.configure_item(horizontal, p1=(x - s, y), p2=(x + s, y))
        dpg.configure_item(vertical, p1=(x, y - s), p2=(x, y + s))

    def _clicked(self, sender=None, app_data=None, user_data=None) -> None:
        """The card was clicked."""
        if self.on_click:
            self.on_click()

import dearpygui.dearpygui as dpg
from datetime import datetime
from ...core.consumer import Consumer
from ...core.logging import logger


class LiveLogWindow(Consumer):
    async def run(self):
        """
        Run the live log window.
        """
        logger.debug("[GUI] Running live log window")

        window_tag = dpg.generate_uuid()
        window_width = 600

        try:
            while True:
                log = await self.consume(timeout=0.25)
                viewport_width = dpg.get_viewport_client_width()
                viewport_height = dpg.get_viewport_client_height()
                x_pos = viewport_width - window_width - 20

                # if log is not None:
                #     print("log received")
                # else:
                #     print("no log received")

                with dpg.window(
                    label="Logs",
                    pos=[x_pos, 40],
                    width=window_width,
                    height=viewport_height - 100,
                    no_close=True,
                    no_collapse=True,
                    no_background=True,
                    no_resize=True,
                    no_move=True,
                    no_bring_to_front_on_focus=True,
                    no_focus_on_appearing=True,
                    tag=window_tag,
                ):
                    if log is not None:
                        timestamp = datetime.fromtimestamp(log["time"]).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        with dpg.group(horizontal=True, parent=window_tag):
                            if log["level"] == "error":
                                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                                dpg.add_text(f"[{log['level']}]", color=(255, 171, 91))
                                dpg.add_text(f"{log['message']}", color=(255, 255, 255))
                            elif log["level"] == "warning":
                                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                                dpg.add_text(f"[{log['level']}]", color=(255, 171, 91))
                                dpg.add_text(f"{log['message']}", color=(255, 255, 255))
                            elif log["level"] == "info":
                                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                                dpg.add_text(f"[{log['level']}]", color=(128, 196, 233))
                                dpg.add_text(f"{log['message']}", color=(255, 255, 255))
                            elif log["level"] == "debug":
                                dpg.add_text(f"[{timestamp}]", color=(0, 135, 158))
                                dpg.add_text(f"[{log['level']}]", color=(0, 135, 158))
                                dpg.add_text(f"{log['message']}", color=(175, 175, 175))
                            else:
                                dpg.add_text(f"[{timestamp}]", color=(128, 196, 233))
                                dpg.add_text(f"[{log['level']}]", color=(128, 196, 233))
                                dpg.add_text(f"{log['message']}", color=(255, 255, 255))

        except Exception as e:
            logger.error(f"Error in live log window: {e}")

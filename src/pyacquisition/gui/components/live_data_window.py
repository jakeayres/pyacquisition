import dearpygui.dearpygui as dpg
import time
from ...core.consumer import Consumer
from ...core.logging import logger
from ..constants import EMPHASIS_COLOR, SECONDARY_COLOR, WHITE




class LiveDataWindow(Consumer):


    async def run(self):
        """
        Run the live data window.
        """
        logger.debug("[GUI] Running live data window")
        
        self.window_tag = dpg.generate_uuid()
        
        try:
            with dpg.window(
                label="Live Data",
                pos=[20, 140],
                width=300,
                height=750,
                no_close=True,
                no_collapse=True,
                no_background=True,
                no_resize=True,
                no_move=True,
                no_bring_to_front_on_focus=True,
                no_focus_on_appearing=True,
                tag=self.window_tag,
            ):
                t0 = time.time()
                data = await self.consume()
                t1 = time.time()
                key_tags = {}
                value_tags = {}
                time_tag = dpg.generate_uuid()
                for key, value in data.items():
                    with dpg.group(horizontal=True, parent=self.window_tag):
                        tag = dpg.generate_uuid()
                        key_tags[key] = tag
                        dpg.add_text(f"{key:{' '}<{15}}", tag=tag, color=SECONDARY_COLOR)
                        
                        tag = dpg.generate_uuid()
                        value_tags[key] = tag
                        dpg.add_text(f"{value:{' '}<{15}}", tag=tag)
                with dpg.group(horizontal=True, parent=self.window_tag):
                    dpg.add_text("Loop Time      ",  color=EMPHASIS_COLOR)
                    dpg.add_text(f"{t1-t0:.3f} s", tag=time_tag, color=WHITE)
                    
                while True:
                    t0 = time.time()
                    data = await self.consume()
                    for key, value in data.items():
                        if key in key_tags:
                            dpg.set_value(key_tags[key], f"{key:{' '}<{15}}")
                            dpg.set_value(value_tags[key], f"{value:{' '}<{15}}")
                        else:
                            logger.warning(f"Key {key} not found in key_tags")
                    t1 = time.time()
                    dpg.set_value(time_tag, f"{t1-t0:.3f} s")
                    
                    
        except Exception as e:
            logger.error(f"[LiveDataWindow] Error running live data window: {e}")
                
    
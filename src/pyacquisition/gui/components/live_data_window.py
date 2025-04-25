import dearpygui.dearpygui as dpg
from ...core.broadcaster import Broadcaster
from ...core.logging import logger



class LiveDataWindow:


    async def run(self):
        """
        Run the live data window.
        """
        logger.debug("Running live data window")
        
        # while True:
        #     try:
        #         await self._pause_event.wait()
        #         data = await self.consume()
        #         data = pd.DataFrame(data=data, index=[0])
        #         self.process_line(data)
                
        #     except Exception as e:
        #         logger.error(f"[LiveDataWindow] Error running main loop: {e}")

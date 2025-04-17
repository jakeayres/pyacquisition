import dearpygui.dearpygui as dpg
import asyncio
from ..core.logging import logger
from multiprocessing import Process


class Gui:
    
    
    def setup(self):
        """
        Setup the GUI.
        """
        logger.debug("GUI setup started")
        dpg.create_context()
        dpg.create_viewport(title='PyAcquisition GUI')
        dpg.setup_dearpygui()
        logger.debug("GUI setup completed")
        
    
    async def run(self):
        """
        The main loop that runs the GUI.
        """
        logger.debug("Running GUI")
        dpg.show_viewport()
        # dpg.start_dearpygui()
        
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            await asyncio.sleep(0.01)
        
        
    def teardown(self):
        """
        Teardown the GUI.
        """
        logger.debug("GUI teardown started")
        dpg.destroy_context()
        logger.debug("GUI teardown completed")
            
    
    def run_with_asyncio(self):
        """
        Run the GUI in the main thread using asyncio.
        """
        try:
            self.setup()
            asyncio.run(self.run())
        except KeyboardInterrupt:
            logger.info("GUI closed by user")
        finally:
            self.teardown()
        
    
    def run_in_new_process(self):
        """
        Run the GUI in a new process.
        """
        process = Process(target=self.run_with_asyncio)
        process.start()
        return process

        

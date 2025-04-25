import dearpygui.dearpygui as dpg
import asyncio
from ..core.logging import logger
from multiprocessing import Process
from .api_client import APIClient
from .openapi import Schema
from .components.endpoint_popup import EndpointPopup
import json
from functools import partial


class Gui:
    
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__()
        
        self.api_client = APIClient(host=host, port=port)
        
        self.runnables = {}
        self.popups = []
     
     
    def add_runnable(self, name: str, runnable):
        """
        Add a runnable to the GUI.
        """
        if name in self.runnables:
            logger.warning(f"Runnable {name} already exists. Overwriting.")
        self.runnables[name] = runnable
        
    
    def remove_runnable(self, name: str):
        """
        Remove a runnable from the GUI.
        """
        if name in self.runnables:
            del self.runnables[name]
            logger.debug(f"Runnable {name} removed")
        else:
            logger.warning(f"Runnable {name} not found")
    
    
    async def _render(self):
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            await asyncio.sleep(0.010)
            
            
    async def _run_runnables(self):
        for name, runnable in self.runnables.items():
            if hasattr(runnable, 'run'):
                await runnable.run()
            else:
                logger.warning(f"Runnable {name} does not have a run method")
            
    
    async def _fetch_openapi_schema(self):
        try:
            logger.debug("Fetching OpenAPI schema")
            data = await self.api_client.async_get(f"/openapi.json")
            return Schema(data)
        except Exception as e:
            logger.error(f"Error fetching OpenAPI schema: {e}")
            return None
        
        
    async def _fetch_instruments(self):
        try:
            logger.debug("Fetching instruments")
            data = await self.api_client.async_get(f"/rack/list_instruments")
            logger.debug(f"Instruments: {data}")   
            return data.get('instruments', [])
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return None
        
        
    async def _fetch_measurements(self):
        try:
            logger.debug("Fetching measurements")
            data = await self.api_client.async_get(f"/rack/list_measurements")
            logger.debug(f"Measurements: {data}")   
            return data.get('measurements', [])
        except Exception as e:
            logger.error(f"Error fetching measurements: {e}")
            return None
        
        
    def _draw_popup(self, sender, app_data, user_data):
        logger.debug(f"Drawing popup for path: {user_data["path"],}")
        popup = EndpointPopup(
            path=user_data["path"],
            api_client=self.api_client,
        )
        self.popups.append(popup)
        popup.draw()


    async def _populate_scribe(self, schema: Schema):
        """
        Populate the scribe in the GUI.
        """
        logger.debug("Populating scribe")
     
        with dpg.viewport_menu_bar():
             with dpg.menu(label="Scribe"):
                for name, path in schema.paths.items():
                    if name.startswith(f"/scribe"):
                        dpg.add_menu_item(
                            label=path.get.summary, 
                            callback=self._draw_popup,
                            user_data={"path": path},
                            )
                               
        
        
    async def _populate_instruments(self, schema: Schema):
        """
        Populate the instruments in the GUI.
        """
        logger.debug("Populating instruments")
        instruments = await self._fetch_instruments()
        
        if instruments is None:
            logger.error("No instruments found")
            return
        
        with dpg.viewport_menu_bar():
             with dpg.menu(label="Instruments"):
                for instrument_name, instrument in instruments.items():
                    logger.debug(f"Adding instrument {instrument}")
                    with dpg.menu(label=instrument_name):
                        for name, path in schema.paths.items():
                            if name.startswith(f"/{instrument_name}"):
                                dpg.add_menu_item(
                                    label=path.get.summary, 
                                    callback=self._draw_popup,
                                    user_data={"path": path},
                                    )
                                
    
    async def setup(self):
        """
        Setup the GUI.
        """
        logger.debug("GUI setup started")
        dpg.create_context()
        dpg.create_viewport(title='PyAcquisition GUI')
        dpg.setup_dearpygui()
        
        with dpg.viewport_menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
        
        schema = await self._fetch_openapi_schema()
        
        await self._populate_scribe(schema)
        await self._populate_instruments(schema)
        
        measurements = await self._fetch_measurements()
        logger.debug(f"Measurements: {measurements}")
        

        logger.debug("GUI setup completed")
        
    
    async def run(self):
        """
        The main loop that runs the GUI.
        """
        logger.debug("Running GUI")
        dpg.show_viewport()
        
        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(self._render())
            task_group.create_task(self._run_runnables())

          
    async def teardown(self):
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
            asyncio.run(self.setup())
            asyncio.run(self.run())
        except KeyboardInterrupt:
            logger.info("GUI closed by user")
        except Exception as e:
            logger.error(f"Error running GUI: {e}")
        finally:
            asyncio.run(self.teardown())
        
    
    def run_in_new_process(self):
        """
        Run the GUI in a new process.
        """
        process = Process(target=self.run_with_asyncio)
        process.start()
        return process

        

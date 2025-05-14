import dearpygui.dearpygui as dpg
import asyncio
from ..core.logging import logger
from multiprocessing import Process
from .api_client import APIClient
from .openapi import Schema
from .dataframe import DataFrame
from .components.endpoint_popup import EndpointPopup
from .components.live_data_window import LiveDataWindow
from .components.live_log_window import LiveLogWindow
from .components.live_plot import LivePlotWidget
from .components.file_window import FileWindow
from .components.task_manager_window import TaskManagerWindow


class Gui:
    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__()

        self.api_client = APIClient(host=host, port=port)
        self.dataframe = DataFrame()
        self.live_data_window = LiveDataWindow()
        self.live_log_window = LiveLogWindow()

    async def _render(self):
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            await asyncio.sleep(0.010)

    async def _fetch_openapi_schema(self):
        try:
            logger.debug("Fetching OpenAPI schema")
            data = await self.api_client.async_get("/openapi.json")
            return Schema(data)
        except Exception as e:
            logger.error(f"Error fetching OpenAPI schema: {e}")
            return None

    async def _fetch_instruments(self):
        try:
            logger.debug("Fetching instruments")
            data = await self.api_client.async_get("/rack/list_instruments")
            logger.debug(f"Instruments: {data}")
            return data.get("instruments", [])
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return None

    async def _fetch_measurements(self):
        try:
            logger.debug("Fetching measurements")
            data = await self.api_client.async_get("/rack/list_measurements")
            logger.debug(f"Measurements: {data}")
            return data.get("measurements", [])
        except Exception as e:
            logger.error(f"Error fetching measurements: {e}")
            return None

    def _draw_popup(self, sender, app_data, user_data):
        logger.debug(f"Drawing popup for path: {(user_data['path'],)}")
        popup = EndpointPopup(
            path=user_data["path"],
            api_client=self.api_client,
        )
        popup.draw()

    async def _populate_scribe(self, schema: Schema):
        """
        Populate the scribe in the GUI.
        """
        logger.debug("Populating scribe")

        with dpg.viewport_menu_bar():
            with dpg.menu(label="Scribe"):
                for name, path in schema.paths.items():
                    if name.startswith("/scribe"):
                        dpg.add_spacer(height=1)
                        dpg.add_menu_item(
                            label=f" {path.get.summary:{' '}<{15}}",
                            callback=self._draw_popup,
                            user_data={"path": path},
                        )
                dpg.add_spacer(height=1)

    async def _populate_rack(self, schema: Schema):
        """
        Populate the scribe in the GUI.
        """
        logger.debug("Populating rack")

        with dpg.viewport_menu_bar():
            with dpg.menu(label="Rack"):
                for name, path in schema.paths.items():
                    if name.startswith("/rack"):
                        dpg.add_spacer(height=1)
                        dpg.add_menu_item(
                            label=f" {path.get.summary:{' '}<{15}}",
                            callback=self._draw_popup,
                            user_data={"path": path},
                        )
                dpg.add_spacer(height=1)

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
                    dpg.add_spacer(height=1)
                    with dpg.menu(label=f" {instrument_name:{' '}<{15}}"):
                        for name, path in schema.paths.items():
                            if name.startswith(f"/{instrument_name}"):
                                dpg.add_spacer(height=1)
                                dpg.add_menu_item(
                                    label=f" {path.get.summary:{' '}<{15}}",
                                    callback=self._draw_popup,
                                    user_data={"path": path},
                                )
                        dpg.add_spacer(height=1)
                dpg.add_spacer(height=1)

    async def _populate_task_manager(self, schema: Schema):
        """
        Populate the task manager in the GUI.
        """
        logger.debug("Populating task manager")

        with dpg.viewport_menu_bar():
            with dpg.menu(label="Task Manager"):
                for name, path in schema.paths.items():
                    if name.startswith("/task_manager"):
                        dpg.add_spacer(height=1)
                        dpg.add_menu_item(
                            label=f" {path.get.summary:{' '}<{15}}",
                            callback=self._draw_popup,
                            user_data={"path": path},
                        )
                dpg.add_spacer(height=1)

    async def _populate_tasks(self, schema: Schema):
        """
        Populate the tasks in the GUI.
        """
        logger.debug("Populating tasks")

        with dpg.viewport_menu_bar():
            with dpg.menu(label="Tasks"):
                for name, path in schema.paths.items():
                    if name.startswith("/tasks"):
                        dpg.add_spacer(height=1)
                        dpg.add_menu_item(
                            label=f" {path.get.summary:{' '}<{15}}",
                            callback=self._draw_popup,
                            user_data={"path": path},
                        )
                dpg.add_spacer(height=1)

    async def _populate_plots(self):
        """
        Populate the plots menu in the GUI.
        """
        logger.debug("Populating plots menu")

        with dpg.viewport_menu_bar():
            with dpg.menu(label="Plots"):
                dpg.add_spacer(height=1)
                dpg.add_menu_item(label="New Plot", callback=self.new_plot)
                dpg.add_spacer(height=1)

    def new_plot(self, sender, app_data, user_data):
        plot = LivePlotWidget(self.dataframe.data)
        self.dataframe.add_callback(plot.update)
        plot.set_on_close(lambda: self.dataframe.remove_callback(plot.update))

    def shutdown(self):
        """
        Shutdown the GUI.
        """
        logger.debug("Shutting down GUI")
        self.api_client.get("/experiment/shutdown")
        dpg.stop_dearpygui()
        logger.debug("GUI shutdown completed")

    async def setup(self):
        """
        Setup the GUI.
        """
        logger.warning("[GUI] Setup started")
        dpg.create_context()
        dpg.create_viewport(
            title="PyAcquisition GUI", width=1440, height=900, disable_close=True
        )
        dpg.setup_dearpygui()

        # with dpg.viewport_menu_bar():
        #     with dpg.menu(label="File"):
        #         dpg.add_menu_item(label="Exit", callback=self.shutdown)

        dpg.set_exit_callback(self.shutdown)

        schema = await self._fetch_openapi_schema()

        await self._populate_scribe(schema)
        await self._populate_rack(schema)
        await self._populate_instruments(schema)
        await self._populate_task_manager(schema)
        await self._populate_tasks(schema)
        await self._populate_plots()

        measurements = await self._fetch_measurements()
        logger.debug(f"Measurements: {measurements}")

        # Steams
        self.api_client.add_stream("logs", "/logs")
        self.api_client.add_stream("data", "/data")
        self.dataframe.subscribe_to(self.api_client.streams["data"])
        self.live_data_window.subscribe_to(self.dataframe)
        self.live_log_window.subscribe_to(self.api_client.streams["logs"])

        # Pollers
        file_poller = self.api_client.add_poller(
            "current_file", "/scribe/current_file", period=1.0
        )
        directory_poller = self.api_client.add_poller(
            "current_directory", "/scribe/current_directory", period=1.0
        )
        current_task_poller = self.api_client.add_poller(
            "current_task", "/task_manager/current_task", period=1.0
        )
        task_manager_status_poller = self.api_client.add_poller(
            "task_manager_status", "/task_manager/status", period=1.0
        )
        task_queue_poller = self.api_client.add_poller(
            "task_queue", "/task_manager/task_list", period=1.0
        )

        file_window = FileWindow()
        file_poller.add_callback(
            lambda message: file_window.update_file(message["data"])
        )
        directory_poller.add_callback(
            lambda message: file_window.update_directory(message["data"])
        )

        task_window = TaskManagerWindow()
        current_task_poller.add_callback(
            lambda message: task_window.update_current_task(message["data"])
        )
        task_manager_status_poller.add_callback(
            lambda message: task_window.update_running_status(message["data"])
        )
        task_queue_poller.add_callback(
            lambda message: task_window.update_task_queue(message["data"])
        )

        logger.debug("[GUI] Setup completed")

    async def run(self):
        """
        The main loop that runs the GUI.
        """
        logger.debug("Running GUI")
        dpg.show_viewport()

        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(self._render())
            task_group.create_task(self.api_client.run())
            task_group.create_task(self.dataframe.run())
            task_group.create_task(self.live_data_window.run())
            task_group.create_task(self.live_log_window.run())

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
        from ..core.logging import logger

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
        return process

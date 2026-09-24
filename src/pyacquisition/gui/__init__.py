import dearpygui.dearpygui as dpg
from ..core.logging import logger
from multiprocessing import Process
from .api_client import APIClient
from .openapi import Schema
from .dataframe import DataFrame
from .managers import MAIN, control_path, task_paths
from .components.confirm_popup import confirm
from .components.endpoint_popup import EndpointPopup
from .components.live_data_window import LiveDataWindow
from .components.live_log_window import LiveLogWindow
from .components.plot_panel import PlotPanel
from .components.file_window import FileWindow
from .components.instruments_window import InstrumentsWindow
from .components.sidebar import Sidebar
from .components.task_manager_window import TaskManagerWindow


PAGES = ("Experiment", "Task Queue", "Instruments", "Logs")  # the tabs of the menu


class Gui:
    def __init__(
        self, host: str = "localhost", port: int = 8000, sparkline_points: int = 100
    ):
        """
        Args:
            host (str): The host of the API server.
            port (int): The port of the API server.
            sparkline_points (int): How many of the latest points the small graph
                beside each value in the Live Data window shows.
        """
        super().__init__()
        self.sparkline_points = sparkline_points

        # The Gui is pickled when it is sent to the new process, so __init__ holds
        # only plain data. Anything that touches DearPyGui is created in setup(),
        # and the network threads are not started until run().
        self.api_client = APIClient(host=host, port=port)
        self.dataframe = DataFrame()
        self._confirmations = {}  # the abort popup that is open, by task manager
        self._popups = {}  # the endpoint window of each address
        self.pages = {}  # the windows of each page, by its name

    def _fetch_openapi_schema(self):
        try:
            logger.debug("Fetching OpenAPI schema")
            data = self.api_client.get("/openapi.json")
            return Schema(data)
        except Exception as e:
            logger.error(f"Error fetching OpenAPI schema: {e}")
            return None

    def _fetch_instruments(self):
        try:
            logger.debug("Fetching instruments")
            data = self.api_client.get("/rack/list_instruments")
            logger.debug(f"Instruments: {data}")
            return data.get("instruments", [])
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return None

    def _fetch_measurements(self):
        try:
            logger.debug("Fetching measurements")
            data = self.api_client.get("/rack/list_measurements")
            logger.debug(f"Measurements: {data}")
            return data.get("measurements", [])
        except Exception as e:
            logger.error(f"Error fetching measurements: {e}")
            return None

    def _fetch_measurement_sources(self) -> dict:
        """Where each measurement comes from, by name. Empty if it cannot be fetched."""
        try:
            return self.api_client.get("/rack/measurement_sources").get("sources", {})
        except Exception as e:
            logger.error(f"Error fetching measurement sources: {e}")
            return {}

    @staticmethod
    def _addable_tasks(schema, managers: list) -> dict:
        """The endpoints that add a task to the queue of each task manager."""
        if schema is None:
            return {}
        return {name: task_paths(schema, name) for name in managers}

    def _add_task(self, manager: str, path) -> None:
        """
        Open the window for adding a task that was picked from the list at the bottom of
        a queue, which asks for its inputs and adds it.

        Args:
            manager (str): The task manager whose queue it is added to.
            path: The endpoint that adds the task.
        """
        managers = self.task_window.panels
        self._draw_popup(
            None,
            None,
            {"path": path, "manager": manager if len(managers) > 1 else None},
        )

    def _next_file(self, title: str, next_block: bool = False) -> None:
        """
        Start the next file, with a title, and show it at once rather than at the next
        refresh.

        Args:
            title (str): The title of the next file.
            next_block (bool): Whether to start a new block, and not the next step.
        """
        try:
            logger.debug(f"[GUI] Starting the next file, '{title}'")
            params = {"title": title, "next_block": next_block}
            self.api_client.get("/scribe/next_file", params=params, timeout=5)
            file = self.api_client.get("/scribe/current_file", timeout=5)
            self.file_window.update_file(file["data"])
        except Exception as e:
            logger.error(f"[GUI] Could not start the next file: {e}")

    def _show_rack_state(self, state: dict) -> None:
        """Show whether the measurements are paused, and the time between them."""
        self.live_data_window.set_paused(state["paused"])
        if "period" in state:
            self.live_data_window.set_period(state["period"])

    def _set_measurement_period(self, seconds: float) -> None:
        """
        Set the time between measurements, and show what the experiment has after it.

        Args:
            seconds (float): The time between measurements.
        """
        try:
            logger.debug(f"[GUI] Setting the measurement period to {seconds}")
            self.api_client.get("/rack/period/set/", params={"period": seconds}, timeout=5)
            state = self.api_client.get("/rack/state", timeout=5)
            self.live_data_window.period_card.set_value(state["period"], force=True)
        except Exception as e:
            logger.error(f"[GUI] Could not set the measurement period: {e}")

    def _toggle_measurements(self, paused: bool) -> None:
        """
        Pause the measurements, or resume them if they are paused, and show the result
        at once rather than at the next refresh.

        Args:
            paused (bool): Whether they are paused now.
        """
        action = "resume" if paused else "pause"
        try:
            logger.debug(f"[GUI] {action} the measurements")
            self.api_client.get(f"/rack/{action}/", timeout=5)
            state = self.api_client.get("/rack/state", timeout=5)
            self.live_data_window.set_paused(state["paused"])
        except Exception as e:
            logger.error(f"[GUI] Could not {action} the measurements: {e}")

    def _fetch_task_managers(self) -> list:
        """
        The names of the task managers, main first. Falls back to just `main`.
        """
        try:
            logger.debug("Fetching task managers")
            names = self.api_client.get("/managers")["data"]
            return names or [MAIN]
        except Exception as e:
            logger.error(f"Error fetching task managers: {e}")
            return [MAIN]

    def _toggle_task_manager(self, name: str, paused: bool) -> None:
        """
        Pause a task manager, or resume it if it is paused, and show the result at
        once rather than at the next refresh.

        Args:
            name (str): The name of the task manager.
            paused (bool): Whether it is paused now.
        """
        self._send_task_manager_action(name, "resume" if paused else "pause")

    def _abort_task_manager(self, name: str, task_name: str) -> None:
        """
        Ask before aborting the task that a task manager is running, because it
        cannot be undone. Nothing is sent unless it is confirmed.

        Args:
            name (str): The name of the task manager.
            task_name (str): The name of the task that it is running.
        """
        popup = self._confirmations.get(name)
        if popup is not None and popup.is_open:
            return  # already asking

        self._confirmations[name] = confirm(
            title=f"Abort {task_name}?",
            message=(
                f"Abort '{task_name}' on the '{name}' task manager?\n\n"
                "The task stops at its next step and runs its teardown. The task "
                "manager is then paused, so nothing else starts until you press "
                "Resume."
            ),
            on_confirm=lambda: self._send_task_manager_action(name, "abort"),
            confirm_label="Abort",
            danger=True,
        )

    def _remove_queued_task(self, name: str, task_id: str, task_name: str) -> None:
        """
        Remove a task from a task manager's queue. The task is picked out by its id,
        so it is the right one even if the queue has moved on since it was drawn.

        Args:
            name (str): The name of the task manager.
            task_id (str): The id of the task.
            task_name (str): The name of the task, for the log.
        """
        logger.debug(f"[GUI] remove '{task_name}' from the queue of '{name}'")
        self._send_task_manager_action(
            name, "remove_queued_task", params={"task_id": task_id}
        )

    def _move_queued_task(
        self, name: str, task_id: str, task_name: str, direction: str
    ) -> None:
        """
        Move a task one place along a task manager's queue. The task is picked out
        by its id, so it is the right one even if the queue has moved on since it was
        drawn.

        Args:
            name (str): The name of the task manager.
            task_id (str): The id of the task.
            task_name (str): The name of the task, for the log.
            direction (str): `up`, so that it runs sooner, or `down`.
        """
        logger.debug(f"[GUI] move '{task_name}' {direction} in the queue of '{name}'")
        self._send_task_manager_action(
            name,
            "move_queued_task",
            params={"task_id": task_id, "direction": direction},
        )

    def _send_task_manager_action(
        self, name: str, action: str, params: dict | None = None
    ) -> None:
        """
        Pause, resume, abort or remove a task from a task manager, and show the
        result at once.

        Args:
            name (str): The name of the task manager.
            action (str): `pause`, `resume`, `abort` or `remove_queued_task`.
            params (dict | None): The parameters of the request, if it has any.
        """
        try:
            logger.debug(f"[GUI] {action} task manager '{name}'")
            self.api_client.get(control_path(name, action), params=params, timeout=5)
            states = self.api_client.get("/managers/state", timeout=5)["data"]
            self.task_window.update(states)
        except Exception as e:
            logger.error(f"[GUI] Could not {action} task manager '{name}': {e}")

    def _draw_popup(self, sender, app_data, user_data):
        """
        Open the window for an endpoint. If it is open already, bring it to the front
        instead of opening another. Each new window is a little below and to the right
        of the last, so that they do not sit exactly on top of one another.
        """
        path = user_data["path"]
        logger.debug(f"Drawing popup for path: {path.path}")

        popup = self._popups.get(path.path)
        if popup is not None and popup.is_open:
            popup.focus()
            return

        self._popups = {k: p for k, p in self._popups.items() if p.is_open}
        step = len(self._popups) % 8
        popup = EndpointPopup(
            path=path, api_client=self.api_client, manager=user_data.get("manager")
        )
        popup.draw(pos=(400 + 30 * step, 90 + 30 * step))
        self._popups[path.path] = popup

    def show_page(self, name: str) -> None:
        """
        Show a page, in the left part of the window, and hide the others. The right seven twelfths
        is for the plots, and is the same on every page.

        Args:
            name (str): The name of the page, one of `PAGES`.

        Raises:
            ValueError: If there is no such page.
        """
        if name not in self.pages:
            raise ValueError(f"page must be one of {', '.join(self.pages)}, got {name!r}")
        for page, windows in self.pages.items():
            for window in windows:
                dpg.configure_item(window, show=page == name)

    @staticmethod
    def _instrument_endpoints(schema, instruments: dict) -> dict:
        """The endpoints of each instrument: its queries and commands, by its name."""
        if schema is None:
            return {}
        return {
            name: [
                path
                for endpoint, path in schema.paths.items()
                if endpoint.startswith(f"/{name}/")  # not "furnace" matching "furnace_pid"
            ]
            for name in instruments
        }

    def _pick_instrument_endpoint(self, instrument: str, path) -> None:
        """
        Open the window that asks for the inputs of an endpoint that was picked from the
        list of an instrument, and sends the request.
        """
        self._draw_popup(None, None, {"path": path, "manager": None})

    def shutdown(self):
        """
        Shutdown the GUI.
        """
        logger.debug("Shutting down GUI")
        self.api_client.get("/experiment/shutdown")
        dpg.stop_dearpygui()
        logger.debug("GUI shutdown completed")

    def setup(self):
        """
        Setup the GUI.
        """
        logger.warning("[GUI] Setup started")
        dpg.create_context()
        dpg.create_viewport(
            title="PyAcquisition GUI", width=1920, height=900, disable_close=True
        )
        dpg.setup_dearpygui()

        # The menu, down the left of the window, whose tabs are the pages.
        self.sidebar = Sidebar(pages=PAGES, on_select=self.show_page)

        dpg.set_exit_callback(self.shutdown)

        schema = self._fetch_openapi_schema()

        managers = self._fetch_task_managers()

        measurements = self._fetch_measurements()
        logger.debug(f"Measurements: {measurements}")

        # Windows
        self.live_data_window = LiveDataWindow(
            sources=self._fetch_measurement_sources(),
            on_toggle=self._toggle_measurements,
            on_period=self._set_measurement_period,
        )
        self.live_log_window = LiveLogWindow()
        # The plot fills the right seven twelfths of the window, whichever page is shown.
        self.plot_panel = PlotPanel(
            colors=lambda key: self.live_data_window.colors.get(key)
        )
        self.file_window = FileWindow(on_next_file=self._next_file)
        self.task_window = TaskManagerWindow(
            managers,
            on_toggle=self._toggle_task_manager,
            on_abort=self._abort_task_manager,
            on_remove=self._remove_queued_task,
            on_move=self._move_queued_task,
            tasks=self._addable_tasks(schema, managers),
            on_add=self._add_task,
        )

        instruments = self._fetch_instruments() or {}
        self.instruments_window = InstrumentsWindow(
            on_pick=self._pick_instrument_endpoint
        )
        self.instruments_window.set_instruments(
            instruments, self._instrument_endpoints(schema, instruments)
        )

        # The pages: what is shown in the left part of the window for each tab.
        self.pages = {
            "Experiment": [
                self.file_window.window_tag,
                self.live_data_window.window_tag,
            ],
            "Task Queue": [self.task_window.window_tag],
            "Instruments": [self.instruments_window.window_tag],
            "Logs": [self.live_log_window.window_tag],
        }
        self.show_page(PAGES[0])

        # Streams
        data_stream = self.api_client.add_stream("data", "/data")
        log_stream = self.api_client.add_stream("logs", "/logs")
        data_stream.add_callback(self.dataframe.update)
        self.dataframe.add_callback(self.live_data_window.update)
        self.dataframe.add_callback(self.plot_panel.update)
        log_stream.add_callback(self.live_log_window.add_log)

        # Pollers
        file_poller = self.api_client.add_poller(
            "current_file", "/scribe/current_file", period=1.0
        )
        directory_poller = self.api_client.add_poller(
            "current_directory", "/scribe/current_directory", period=1.0
        )
        task_managers_poller = self.api_client.add_poller(
            "task_managers", "/managers/state", period=1.0
        )

        rack_poller = self.api_client.add_poller("rack_state", "/rack/state", period=1.0)
        rack_poller.add_callback(self._show_rack_state)

        file_poller.add_callback(
            lambda message: self.file_window.update_file(message["data"])
        )
        directory_poller.add_callback(
            lambda message: self.file_window.update_directory(message["data"])
        )
        task_managers_poller.add_callback(
            lambda message: self.task_window.update(message["data"])
        )

        logger.debug("[GUI] Setup completed")

    def run(self):
        """
        The DearPyGui render loop. Runs on the main thread: incoming data is
        handed to the widgets, then the frame is rendered.
        """
        logger.debug("Running GUI")
        self.api_client.start()
        dpg.show_viewport()

        while dpg.is_dearpygui_running():
            self.api_client.dispatch()
            self.live_log_window.update_layout()
            self.live_log_window.tick()
            self.instruments_window.update_layout()
            self.sidebar.tick()
            self.file_window.fit()
            self.task_window.tick()
            self.live_data_window.tick()
            self.plot_panel.update_layout()
            self.plot_panel.tick()
            dpg.render_dearpygui_frame()

    def teardown(self):
        """
        Teardown the GUI.
        """
        logger.debug("GUI teardown started")
        self.api_client.stop()
        dpg.destroy_context()
        logger.debug("GUI teardown completed")

    def main(self):
        """
        Set up, run and tear down the GUI on the calling thread.
        """
        try:
            self.setup()
            self.run()
        except KeyboardInterrupt:
            logger.info("GUI closed by user")
        except Exception as e:
            logger.error(f"Error running GUI: {e}")
        finally:
            self.teardown()

    def run_in_new_process(self):
        """
        Run the GUI in a new process.
        """
        process = Process(target=self.main)
        return process

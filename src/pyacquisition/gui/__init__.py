import dearpygui.dearpygui as dpg
from ..core.logging import logger
from multiprocessing import Process
from .api_client import APIClient
from .openapi import Schema
from .dataframe import DataFrame
from .managers import MAIN, control_path, management_paths, task_paths
from .components.confirm_popup import confirm
from .components.endpoint_popup import EndpointPopup
from .components.live_data_window import LiveDataWindow
from .components.live_log_window import LiveLogWindow
from .components.live_plot import LivePlotWidget
from .components.file_window import FileWindow
from .components.task_manager_window import TaskManagerWindow


class Gui:
    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__()

        # The Gui is pickled when it is sent to the new process, so __init__ holds
        # only plain data. Anything that touches DearPyGui is created in setup(),
        # and the network threads are not started until run().
        self.api_client = APIClient(host=host, port=port)
        self.dataframe = DataFrame()
        self._confirmations = {}  # the abort popup that is open, by task manager

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
        logger.debug(f"Drawing popup for path: {(user_data['path'],)}")
        popup = EndpointPopup(
            path=user_data["path"],
            api_client=self.api_client,
            title=user_data.get("title"),
        )
        popup.draw()

    def _add_endpoint_items(self, paths: list, manager: str | None = None) -> None:
        """
        Add a menu item for each endpoint. Given a manager, its popups are titled
        with its name, so that "Pause" on two task managers can be told apart.
        """
        for path in paths:
            summary = path.get.summary
            dpg.add_spacer(height=1)
            dpg.add_menu_item(
                label=f" {summary:{' '}<{15}}",
                callback=self._draw_popup,
                user_data={
                    "path": path,
                    "title": f"{manager}: {summary}" if manager else None,
                },
            )
        dpg.add_spacer(height=1)

    def _populate_task_manager_menu(self, label: str, paths_for, managers: list):
        """
        Add a menu for the task managers. With only the main one, the entries are
        listed directly. With several, each has a submenu of its own.

        Args:
            label (str): The name of the menu.
            paths_for: Finds the endpoints of a task manager, from its name.
            managers (list): The names of the task managers.
        """
        with dpg.viewport_menu_bar():
            with dpg.menu(label=label):
                if len(managers) == 1:
                    self._add_endpoint_items(paths_for(managers[0]))
                    return

                for name in managers:
                    paths = paths_for(name)
                    if not paths:
                        continue  # nothing to list, such as no tasks registered
                    dpg.add_spacer(height=1)
                    with dpg.menu(label=f" {name:{' '}<{15}}"):
                        self._add_endpoint_items(paths, manager=name)
                dpg.add_spacer(height=1)

    def _populate_scribe(self, schema: Schema):
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

    def _populate_rack(self, schema: Schema):
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

    def _populate_instruments(self, schema: Schema):
        """
        Populate the instruments in the GUI.
        """
        logger.debug("Populating instruments")
        instruments = self._fetch_instruments()

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
                            if name.startswith(
                                f"/{instrument_name}/"
                            ):  # not "furnace" matching "furnace_pid"
                                dpg.add_spacer(height=1)
                                dpg.add_menu_item(
                                    label=f" {path.get.summary:{' '}<{15}}",
                                    callback=self._draw_popup,
                                    user_data={"path": path},
                                )
                        dpg.add_spacer(height=1)
                dpg.add_spacer(height=1)

    def _populate_task_manager(self, schema: Schema, managers: list):
        """
        Populate the task manager menu in the GUI.
        """
        logger.debug("Populating task manager")
        self._populate_task_manager_menu(
            "Task Manager", lambda name: management_paths(schema, name), managers
        )

    def _populate_tasks(self, schema: Schema, managers: list):
        """
        Populate the tasks menu in the GUI.
        """
        logger.debug("Populating tasks")
        self._populate_task_manager_menu(
            "Tasks", lambda name: task_paths(schema, name), managers
        )

    def _populate_plots(self):
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

    def setup(self):
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

        schema = self._fetch_openapi_schema()

        self._populate_scribe(schema)
        self._populate_rack(schema)
        self._populate_instruments(schema)
        managers = self._fetch_task_managers()
        self._populate_task_manager(schema, managers)
        self._populate_tasks(schema, managers)
        self._populate_plots()

        measurements = self._fetch_measurements()
        logger.debug(f"Measurements: {measurements}")

        # Windows
        self.live_data_window = LiveDataWindow()
        self.live_log_window = LiveLogWindow()
        file_window = FileWindow()
        self.task_window = TaskManagerWindow(
            managers,
            on_toggle=self._toggle_task_manager,
            on_abort=self._abort_task_manager,
            on_remove=self._remove_queued_task,
            on_move=self._move_queued_task,
        )

        # Streams
        data_stream = self.api_client.add_stream("data", "/data")
        log_stream = self.api_client.add_stream("logs", "/logs")
        data_stream.add_callback(self.dataframe.update)
        self.dataframe.add_callback(self.live_data_window.update)
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

        file_poller.add_callback(
            lambda message: file_window.update_file(message["data"])
        )
        directory_poller.add_callback(
            lambda message: file_window.update_directory(message["data"])
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
            self.live_data_window.tick()
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

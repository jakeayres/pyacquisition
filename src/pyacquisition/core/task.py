import asyncio
from ..core.logging import logger
from dataclasses import dataclass, fields
from inspect import Signature, Parameter


@dataclass
class Task:
    """Base class for tasks in the experiment framework."""

    @property
    def name(self) -> str:
        """
        Returns the name of the task.
        """
        return self.__class__.__name__

    def __post_init__(self):
        self._pause_event: asyncio.Event = asyncio.Event()
        self._abort_event: asyncio.Event = asyncio.Event()
        self._is_paused: bool = False
        self._status: str = "running"
        self._pause_event.set()  # Set to allow task to run immediately
        self._abort_event.clear()  # Clear to allow task to run immediately

    async def setup(self, experiment=None):
        """
        Override this method in subclasses to define setup tasks.
        """
        pass

    async def teardown(self, experiment=None):
        """
        Override this method in subclasses to define teardown tasks.

        Runs after the task has completed its work even if it was aborted or
        an error occurred.
        """
        pass

    async def run(self, experiment=None):
        """
        Override this method in subclasses to define the task's functionality.
        """
        raise NotImplementedError("Subclasses must implement the run() method.")

    async def start(self, experiment=None):
        """
        Starts the task and manages pausing and aborting.
        """
        self._abort_event.clear()
        try:
            logger.info(f"[{self.name}] Starting task.")
            await self.setup(experiment=experiment)
            async for step in self.run(experiment=experiment):
                if step:
                    logger.info(f"[{self.name}] {step}")
                await self._check_control_flags()
        except asyncio.CancelledError:
            print("Task was cancelled.")
        except Exception as e:
            print(f"Task encountered an error: {e}")
        finally:
            await self.teardown(experiment=experiment)
            logger.info(f"[{self.name}] Task completed.")

    async def _check_control_flags(self):
        """
        Checks for pause or abort signals and handles them.
        Call this method periodically in the user's task logic.
        """
        if self._abort_event.is_set():
            raise asyncio.CancelledError("Task aborted.")
        await self._pause_event.wait()

    @property
    def description(self) -> str:
        """
        Returns a description of the task.
        """
        None

    @property
    def parameters(self) -> dict:
        """
        Returns the displayed parameters of the task.
        """
        None

    def display_dict(self) -> dict:
        """
        Converts the task to a dictionary representation.

        Returns:
            dict: Dictionary representation of the task.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def pause(self):
        """
        Pauses the task.
        """
        self._pause_event.clear()

    def resume(self):
        """
        Resumes the task.
        """
        self._pause_event.set()

    def abort(self):
        """
        Aborts the task.
        """
        self._abort_event.set()
        self._pause_event.set()  # Ensure it doesn't stay paused

    @classmethod
    def register_endpoints(cls, experiment):
        """
        Register the task endpoints with the API server.

        Manually build the endpoint annotations and signature based on the dataclass fields
        and add the endpoint functionanlly in order to dynamically create the endpoint with
        the parameters and type hints.

        Args:
            experiment: The experiment instance to register the endpoints with.
        """

        fields_dict = {field.name: field.type for field in fields(cls)}
        params = [
            Parameter(name, Parameter.POSITIONAL_OR_KEYWORD, annotation=type_)
            for name, type_ in fields_dict.items()
        ]

        async def task_endpoint(**kwargs):
            """
            Endpoint to run the task.

            Returns:
                dict: The result of the task.
            """
            task = cls(**kwargs)
            experiment.task_manager.add_task(task)
            return {"status": 200, "message": f"{cls.__name__} added"}

        task_endpoint.__name__ = f"{cls.__name__}"
        task_endpoint.__annotations__ = fields_dict
        task_endpoint.__annotations__["return"] = dict
        task_endpoint.__signature__ = Signature(
            parameters=params, return_annotation=dict
        )
        task_endpoint.__doc__ = (
            cls.__doc__.split("\n")[0] if cls.__doc__ else "No help available."
        )

        endpoint_path = f"/tasks/{cls.__name__.lower().replace(' ', '_')}"
        experiment._api_server.app.add_api_route(
            endpoint_path,
            task_endpoint,
            methods=["GET"],
            tags=["tasks"],
        )

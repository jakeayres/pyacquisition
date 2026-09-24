from .instrument import resolve_enum_kwargs
from .logging import logger
import inspect
from functools import partial


class Measurement:
    """
    A class to represent a measurement that can be periodically called.
    """

    def __init__(
        self, name: str, function: callable, call_every: int = 1, **kwargs
    ) -> None:
        """
        Initializes the Measurement instance.

        Args:
            name (str): The name of the measurement.
            function (callable): The function to be called for the measurement.
            call_every (int): Call the function every Nth time. Default is 1.
            **kwargs: Additional keyword arguments to pass to the function. Where
                the function takes an enum, give the member (`InputChannel.INPUT_A`)
                or the text that names it (`"INPUT_A"`, or its label `"Input A"`).

        Raises:
            ValueError: If a keyword argument is not one the function takes, or text
                given for an enum does not name a member.

        Example:
            Measurement("T", cryo.get_temperature, input_channel="INPUT_A")
        """
        self._name = name
        self._function = function
        self._call_every = call_every
        self._call_counter = call_every
        self._result = None

        # Validate kwargs against the function's signature
        self._validate_kwargs(function, kwargs)
        # Text such as "INPUT_A" becomes the enum member that it names, here, so that
        # a mistake stops the experiment at setup instead of failing every cycle.
        self._kwargs = resolve_enum_kwargs(function, kwargs)

    @property
    def source(self) -> str:
        """
        Where the value comes from, as `instrument.method`, for showing above its
        name. It is empty if the function is not a method of an instrument.
        """
        function, owner = self._function, None
        while isinstance(function, partial):
            if function.args:
                owner = function.args[0]  # `partial(query, instrument)`
            function = function.func
        owner = getattr(function, "__self__", owner)  # a bound method
        uid = getattr(owner, "_uid", None)
        name = getattr(function, "__name__", "")
        return f"{uid}.{name}" if uid and name else ""

    @staticmethod
    def _validate_kwargs(function: callable, kwargs: dict) -> None:
        """
        Validates that the provided kwargs are valid keyword arguments for the function.

        Args:
            function (callable): The function to validate against.
            kwargs (dict): The keyword arguments to validate.

        Raises:
            ValueError: If any key in kwargs is not a valid keyword argument for the function.
        """
        signature = inspect.signature(function)
        valid_params = signature.parameters

        for key in kwargs:
            if key not in valid_params:
                logger.error(
                    f"Invalid keyword argument '{key}' for function '{function.__name__}'."
                )
                raise ValueError(
                    f"Invalid keyword argument '{key}' for function '{function.__name__}'."
                )

    def run(self):
        """
        Executes the measurement function based on the call_every interval.

        Updates the result only when the call counter reaches 0 or if the result
        is None. Otherwise, it returns the previous result.
        """
        try:
            self._call_counter -= 1
            if self._result is None or self._call_counter == 0:
                self._result = self._function(
                    **self._kwargs
                )  # Pass kwargs to the function
                self._call_counter = self._call_every  # Reset the counter
            return self._result

        except Exception as e:
            logger.error(f"Error in measurement {self._name}: {e}")
            logger.error(f"Returning last result: {self._result}")
            self._call_counter = self._call_every
            return self._result

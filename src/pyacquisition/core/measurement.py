from .logging import logger
import inspect


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
            **kwargs: Additional keyword arguments to pass to the function.
        """
        self._name = name
        self._function = function
        self._call_every = call_every
        self._call_counter = call_every
        self._result = None

        # Validate kwargs against the function's signature
        self._validate_kwargs(function, kwargs)
        self._kwargs = kwargs  # Store additional keyword arguments

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

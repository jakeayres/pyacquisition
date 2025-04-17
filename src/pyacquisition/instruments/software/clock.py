from ..instruments import SoftwareInstrument, mark_query, mark_command
import time


class Clock(SoftwareInstrument):
    """
    A class representing a software clock instrument.
    """
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._t0 = time.time()
        self._named_timers = {}
        
    
    @mark_query
    def time(self) -> float:
        """
        Returns the current time in seconds since the clock was initialized.
        
        Returns:
            float: Current time in seconds.
        """
        return time.time() - self._t0
    
    
    @mark_query
    def timestamp_ms(self) -> int:
        """
        Returns the current timestamp in milliseconds since the clock was initialized.
        
        Returns:
            int: Current timestamp in milliseconds.
        """
        return float(f'{time.time():.3f}')
    
    
    @mark_command
    def start_timer(self, name: str) -> None:
        """
        Starts a timer with the given name.
        
        Args:
            name (str): The name of the timer.
        """
        self._named_timers[name] = time.time()
        return 0
    
    
    @mark_query
    def read_timer(self, name: str) -> float:
        """
        Reads the elapsed time for the given timer.
        
        Args:
            name (str): The name of the timer.
        
        Returns:
            float: Elapsed time in seconds.
        """
        if name not in self._named_timers:
            raise ValueError(f"Timer '{name}' not found.")
        
        return time.time() - self._named_timers[name]
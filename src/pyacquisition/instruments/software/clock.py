from ...core.instrument import SoftwareInstrument, mark_query, mark_command
import time


class Clock(SoftwareInstrument):
    """
    A class representing a software clock instrument.
    """
    
    name = 'Clock'
    
    
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
        Returns the current timestamp in milliseconds since the epoch.
        
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
    def list_timers(self) -> list[str]:
        """
        Lists all active timers.
        
        Returns:
            list[str]: List of active timer names.
        """
        return list(self._named_timers.keys())
    
    
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
    
    
    def register_endpoints(self, api_server):
        super().register_endpoints(api_server)
        
        
        @api_server.app.get("/clock/time", tags=[self._uid])
        async def get_time():
            """Time since clock started in seconds."""
            return {"status": 200, "data": self.time()}
        
        
        @api_server.app.get("/clock/timestamp", tags=[self._uid])
        async def get_timestamp():
            """Current timestamp in milliseconds."""
            return {"status": 200, "data": self.timestamp_ms()}
        
        
        @api_server.app.get("/clock/timer/start", tags=[self._uid])
        async def start_timer(name: str):
            """Start a timer with the given name."""
            self.start_timer(name)
            return {"status": 200, "data": f"Timer '{name}' started."}
        
        
        @api_server.app.get("/clock/timer/list", tags=[self._uid])
        async def list_timers():
            """List all active timers."""
            return {"status": 200, "data": self.list_timers()}
        
        
        @api_server.app.get("/clock/timer/read", tags=[self._uid])
        async def read_timer(name: str):
            """Read the elapsed time for the given timer."""
            try:
                return {"status": 200, "data": self.read_timer(name)}
            except ValueError as e:
                return {"status": 400, "data": "Bad input"}
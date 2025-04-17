from .consumer import Consumer


class Scribe(Consumer):
    
    """
    A class that handles all of the file I/O operations for the data acquisition
    system. This includes reading and writing data to files, as well as managing
    metadata.
    """
    
    def __init__(self, root_path: str) -> None:
        """
        Initialize the Scribe.
        """
        super().__init__()
        
        self.root_path = root_path
        
        
        # Ensure the root_path exists, create it if it doesn't
        self.root_path.mkdir(parents=True, exist_ok=True)
        
        
    def register_endpoints(self, api_server):
        """
        Register the Scribe endpoints with the API server.
        """
        
        @api_server.app.get("/scribe/ping")
        async def ping():
            """
            Endpoint to check if the Scribe is running.
            """
            return {"status": "success", "message": "Scribe is running."}
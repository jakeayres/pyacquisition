from .consumer import Consumer
from .logging import logger
import asyncio
import pandas as pd
import json
from pathlib import Path


class Scribe(Consumer):
    """
    A class that handles all of the file I/O operations for data acquisition.
    This includes reading and writing data to files, as well as managing
    metadata.
    """
    
    def __init__(self, root_path: Path, decimal: bool = True) -> None:
        """
        Initialize the Scribe.
        """
        super().__init__()
        
        self.root_path = root_path
        self.block = '00'
        self.step = '00'
        self.title = "start"
        self.extension = 'data'
        
        self._pause_event = asyncio.Event()
        self._pause_event.set()


    def set_next_unused_block(self) -> str:
        """
        Check the root directory for existing files and determine the next
        block number.
        """
        try:
            files = list(self.root_path.glob(f"{self.block}*"))
            if not files:
                return self.block
            
            files = [file for file in self.root_path.iterdir() if file.is_file() and file.stem[:2].isdigit() and file.stem[2:3] == '.' and file.stem[3:5].isdigit()]
            
            # Extract block numbers from filenames
            block_numbers = [int(file.stem.split('.')[0]) for file in files]
            next_block = max(block_numbers) + 1
            self.block = str(next_block).zfill(2)
            self.step = '00'
            logger.debug(f"[Scribe] Starting at: {self.block}.{self.step}")
        
        except Exception as e:
            logger.error(f"[Scribe] Error getting next block: {e}")


    def next_file(self, title: str, next_block: bool = False) -> None:
        """
        Set the next file to be written to.

        Args:
            title (str): The title of the file.
            next_block (bool): If True, increment the block number. Defaults to False.
        """
        self.title = title
        if next_block:
            self.increment_block()
        else:
            self.increment_step()


    def current_path(self) -> Path:
        """
        Get the current path for the data file.

        Returns:
            Path: The path of the current datafile.
        """
        return self.root_path / f"{self.block}.{self.step} {self.title}.{self.extension}"


    def increment_block(self) -> None:
        """
        Increment the block number.
        """
        self.block = str(int(self.block) + 1).zfill(2)
        self.step = '00'


    def increment_step(self) -> None:

        """
        Increment the step number.
        """
        self.step = str(int(self.step) + 1).zfill(2)


    def make_directory(self, path: Path) -> None:
        """
        Create a directory if it doesn't exist.
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"[Scribe] Directory created: '{path}'")
        except Exception as e:
            logger.error(f"[Scribe] Error creating directory '{path}': {e}")


    def process_line(self, data: pd.DataFrame) -> None:
        """
        Process a line of data.
        """
        try:
            if not self.current_path().exists():
                logger.debug(f"[Scribe] File {self.current_path()} does not exist. Creating new file.")
                self.write_line(data)
            else:
                self.append_line(data)
        except Exception as e:
            logger.error(f"[Scribe] Error processing data: {e}")


    def write_line(self, data: pd.DataFrame) -> None:
        """
        Write a line of data to a file.
        """
        data.to_csv(self.current_path(), index=False, mode='w')


    def append_line(self, data: pd.DataFrame) -> None:
        """
        Append a line of data to a file.
        """
        data.to_csv(self.current_path(), index=False, mode='a', header=False)


    def setup(self):
        """
        Setup the Scribe.
        """
        logger.debug("[Scribe] Setup started")
        self.make_directory(self.root_path)
        self.set_next_unused_block()

        logger.debug("[Scribe] Setup completed")


    async def run(self):
        """
        The main loop that runs the tasks in the queue.
        """
        while True:
            try:
                await self._pause_event.wait()
                data = await self.consume()
                data = pd.DataFrame(data=data, index=[0])
                self.process_line(data)
                
            except Exception as e:
                logger.error(f"[Scribe] Error running main loop: {e}")


    def teardown(self):
        """
        Teardown the Scribe.
        """
        logger.debug("[Scribe] Teardown started")
        logger.debug("[Scribe] Teardown completed")

        
        
    def register_endpoints(self, api_server):
        """
        Register the Scribe endpoints with the API server.
        """

        @api_server.app.get('/scribe/current_file', tags=['scribe'])
        async def current_file_endpoint():
            return {
                "status": 200,
                "data": f"{self.current_path()}",
            }
        

        @api_server.app.get('/scribe/next_file', tags=['scribe'])
        async def next_file_endpoint(title: str, next_block: bool = False):
            self.next_file(title, next_block)
            return {
                "status": 200,
                "data": f"{self.current_path()}",
            }
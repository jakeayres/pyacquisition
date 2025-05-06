from ..core.task import Task
from dataclasses import dataclass


@dataclass
class NewFile(Task):
    """Start a new file

    Attributes:
        file_name (str): The name of the file to be created.
        increment_block (bool): Whether to increment the block number for the new file.
    """

    file_name: str
    increment_block: bool = False

    @property
    def description(self) -> str:
        return f"Starting new file: {self.file_name}. Increment block: {self.increment_block}"

    async def run(self, experiment):
        yield None
        experiment.scribe.next_file(
            title=self.file_name, next_block=self.increment_block
        )
        yield None

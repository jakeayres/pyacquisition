import shutil
from pathlib import Path

from pyacquisition.core.instrument import (
    SoftwareInstrument,
    mark_command,
    mark_query,
)


class DiskSpace(SoftwareInstrument):
    """The space on the drive that the experiment's data is written to."""

    name = "Disk Space"

    def __init__(self, uid):
        super().__init__(uid)
        self._folder = "."

    @mark_query
    def get_space(self) -> float:
        """The free space on the drive, in GB."""
        return shutil.disk_usage(self._folder).free / 1e9

    @mark_command
    def set_folder(self, folder: str) -> None:
        """Watches the drive that a folder is on."""
        if not Path(folder).is_dir():
            raise ValueError(f"There is no folder called {folder!r}.")
        self._folder = folder

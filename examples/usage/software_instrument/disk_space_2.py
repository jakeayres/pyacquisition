import shutil

from pyacquisition.core.instrument import SoftwareInstrument, mark_query


class DiskSpace(SoftwareInstrument):
    """The space on the drive that the experiment's data is written to."""

    name = "Disk Space"

    @mark_query
    def get_space(self) -> float:
        """The free space on the drive, in GB."""
        return shutil.disk_usage(".").free / 1e9

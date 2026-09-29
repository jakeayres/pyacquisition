from pyacquisition.core.instrument import SoftwareInstrument


class DiskSpace(SoftwareInstrument):
    """The space on the drive that the experiment's data is written to."""

    name = "Disk Space"

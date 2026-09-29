from pyacquisition import Experiment


class Lab(Experiment):
    """The rig is in rig.toml. What a file can't say goes here."""

    def setup(self):
        lockin = self.instruments["lockin"]
        lockin.set_frequency(137.0)


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()

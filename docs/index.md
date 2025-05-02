# PyAcquisition

<figure markdown="span">
  ![PyAcquisition](logo.png){ width="500" }
</figure>

`pyacquisition` is a powerful Python package designed to simplify the process of recording scientific data and controlling laboratory instruments. It abstracts away the complexities of instrument communication, task scheduling (both concurrent and sequential), data recording, and logging, allowing you to focus on the science. Whether you're managing a single instrument or orchestrating a complex experimental workflow, `pyacquisition` provides a framework that simplifies the process dramatically.

With `pyacquisition`, you can easily define your experimental setup in a configuration file (written in TOML format) and implement custom functionality by inheriting from the base `Experiment` class. Once configured, running your experiment is as simple as calling `my_experiment.run()`.

## Mission

`pyacquisition` was conceived to be an "all-python" solution to the recording of scientific data.
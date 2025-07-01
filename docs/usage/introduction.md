# Getting Started

The following is a complete step-by-step guide to setting up an experiment. In this walkthrough, we shall: 

1. Initialize a basic experiment
2. Add software (`Clock`) and hardware (`SR_830` lock-in) instruments
3. Add measurements (time and voltages) that are saved to a file
4. Write a custom instrument class (software random number generator)
5. Write a `Task` to automate our experimental procedure

in only a few dozen lines of code. A feature-full GUI allowing you to control the instruments, run your `Task` and visualize the live data will be automatically generated.

It is hoped that the `pyacquisition` API is sufficiently simple that this walkthrough and example code adequately illustrates how to proceed with your own experiment. More verbose descriptions of each step in the code can be found in **:material-plus-circle: annotations** . Where certain internal design choices impose specific and non-obvious requirements, a **:material-pencil-circle: note** can be found under the code.

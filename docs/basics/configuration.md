An experiment can be set up in two ways:

**1. Using a `.toml` file**  

This method is ideal if you only need to use the built-in functionality of `pyacquisition`. Simply create a `.toml` file to define your experiment's configuration. The `.toml` file is read using `Experiment.from_config()`, which automatically calls the necessary methods to set up your experiment.

*Advantages:*

- Simple and requires no Python coding.  
- Access all built-in functionality directly.

**2. Using the `setup()` method**  

This method is for cases where you need custom functionality, such as adding new instruments or tasks. To do this, inherit from `pyacquisition.experiment` and define your custom logic in the `setup()` method. You can define custom instruments and task classes, then import them into your code for use within the `setup()` method.

*Use this method if:*  

- You need to extend the core functionality of `pyacquisition`.  
- You want to define and integrate custom instruments or tasks.  
- You want to import and integrate your own code.

## `.toml` File Configuration

The `.toml` file is used to define the configuration for your experiment. Details of the `.toml` syntax can be found [toml.io](https://toml.io/en/).

Below is a breakdown of the sections and parameters available in the file:

### General Parameters

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `root_path`    | Root directory for the experiment.   | `.`           |


### `[rack]` Section

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `period`       | Time period for rack operations.     | `0.25`        |


### `[instruments]` Section

| Parameter Name | Description                          | Example Line |
|----------------|--------------------------------------|---------------|
| `clock`        | Defines the clock instrument.        | `{instrument = "clock"}` |


### `[measurements]` Section

| Parameter Name | Description                          | Example Line |
|----------------|--------------------------------------|---------------|
| `time`         | Measurement using the clock.         | `{instrument = "clock", method = "timestamp_ms"}` |


### `[data]` Section

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `path`         | Directory for storing data.          | `.`           |


### `[api_server]` Section

| Parameter Name         | Description                          | Default Value          |
|------------------------|--------------------------------------|------------------------|
| `host`                 | Hostname for the API server.         | `localhost`            |
| `port`                 | Port for the API server.             | `8005`                 |
| `allowed_cors_origins` | List of allowed CORS origins.        | `["http://localhost:3000"]` |


### `[logging]` Section

| Parameter Name  | Description                          | Default Value |
|-----------------|--------------------------------------|---------------|
| `console_level` | Logging level for console output.    | `DEBUG`       |
| `file_level`    | Logging level for file output.       | `DEBUG`       |
| `file_name`     | Name of the log file.                | `debug.log`   |



## Configuration with `setup()`

Use the `setup()` method when your experiment requires custom functionality. Define custom instruments and task classes, import them into your code, and integrate them into your experiment within the `setup()` method of your experiment.
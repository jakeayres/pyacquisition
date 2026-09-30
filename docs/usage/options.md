# Set the experiment's options

<p class="pa-meta" markdown="span">About 10 minutes · Needs [Getting Started](../getting_started/python_api.md)</p>

An experiment's **options** say where its data goes, how much the terminal says, which port the interface is on, and how often it measures. Each has a default, so Getting Started set none. In this tutorial you set the ones a real experiment needs: a data folder for each sample and each day, a quieter terminal, a port of its own, and the measuring period. You also see what happens when the class and the config file both set one.

It starts where [2. The Python API](../getting_started/python_api.md) ends: your `my-lab` project, with `rig.toml` and `lab.py`.

<div class="gs" data-files="lab.py:versions rig.toml:versions" data-lines="24" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from the Getting Started lab

```toml title="rig.toml"
--8<-- "examples/usage/options/rig_1.toml"
```

```python title="lab.py"
--8<-- "examples/usage/options/lab_1.py"
```

These are `rig.toml` and `lab.py` as [2. The Python API](../getting_started/python_api.md) left them. `lab.py` makes the experiment from the file, with a calculation, the `Record` task, and the lock-in's setup and teardown.

**More:** [2. The Python API](../getting_started/python_api.md), which builds them.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Keep each sample's data apart

```python title="lab.py" hl_lines="1 25 27-29"
--8<-- "examples/usage/options/lab_2.py"
```

An option is a class attribute of your experiment, named for what it sets. `data_path` is the folder the data files go in. It can be a property that works it out as the experiment starts: here, a folder for each sample and each day, such as `data/sample_A/2026-09-30`. Change `sample` for the next one, and its files have a folder of their own, numbered from `00.00`.

`sample` is a name of your own. The class can hold those too, as long as they aren't close to an option's name.

**More:** [`data_path`, and the rest](../reference/experiment_options.md), and [data files' names](../reference/data_files.md#file-names).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Quieten the terminal

```python title="lab.py" hl_lines="26"
--8<-- "examples/usage/options/lab_3.py"
```

`console_log_level` is the least serious kind of message the terminal shows. The default, `DEBUG`, shows everything the experiment does, which is a lot. `INFO` shows what starts and stops, the files it makes, your tasks' logs, and every warning and error.

The **Logs** tab and the log file have levels of their own, `gui_log_level` and `file_log_level`, and keep everything by default.

**More:** [the log levels](../reference/experiment_options.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Use another port

```python title="lab.py" hl_lines="27-28"
--8<-- "examples/usage/options/lab_4.py"
```

`api_server_port` is the port the interface and the web API are on, 8000 by default. Two experiments on one computer need a port each, and so does anything else already on 8000. `api_server_fallback_ports` are tried in turn if it is taken, and the log says so: `Port 8001 is in use, so the API server is on port 8002 instead`.

**More:** [the `[api_server]` table](../reference/config_file.md#api_server), for the same in a file.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Set the period in the class

```python title="lab.py" hl_lines="29"
--8<-- "examples/usage/options/lab_5.py"
```

`measurement_period` is the time between measuring cycles. But run it now, and the interface still says **Every 0.2 s**: `rig.toml`'s `[rack] period` sets it too, and the file wins over the class.

The order is: an argument to `from_config` first, then the file, then the class, then the default.

**More:** [where a value comes from](../reference/experiment_options.md#where-a-value-comes-from).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Take the period out of the file

```toml title="rig.toml"
--8<-- "examples/usage/options/rig_2.toml"
```

With `[rack]` gone from the file, the class's 0.5 s applies. Keep each option in one place, the file or the class, so that it is clear which is in force.

**More:** [the `[rack]` table](../reference/config_file.md#rack).
{ .gs-more }

</section>

<section class="gs-step" data-result="[Experiment] API server on port 8001" markdown>

## Run the experiment

```bash
uv run lab.py
```

The terminal says only what matters: the port, the folder it made, and the like. The interface is at `http://localhost:8001`, and says **Every 0.5 s**, and the data goes to `data/sample_A/`, today's date, `00.00 start.data`.

**More:** [every option](../reference/experiment_options.md).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    The terminal shows `INFO` and above only. The interface is on port 8001, or the next free one of 8002 and 8003, and says **Every 0.5 s**, and today's data file is in `data/sample_A/` and a folder named for the date.

??? failure "Something not working?"
    - **``TypeError: `console_log_levl` in Lab looks like a misspelling of the option `console_log_level`, so it would do nothing.``** A misspelt option would be ignored without a word, so it is refused as the class is made. Correct the name.
    - **The experiment stops as it starts, with a `ValueError` that ends ``Failed to create Experiment instance: `measurement_period` must be a positive number, got 'fast'``.** Options are checked as the experiment is made, and the end of the message says which, and what it takes.
    - **The period, or another option, isn't the one the class sets.** The file sets it too, and the file wins. Take it out of one of them.
    - **The log says `Port 8001 is in use, so the API server is on port 8002 instead`.** Something else has port 8001, often another experiment. The interface is on 8002: the log's line `API server on port` says which.

## What you learned

- Options are class attributes of your experiment, and one can be a property that works it out.
- `data_path` keeps the data where you want it, `console_log_level` sets how much the terminal says, and `api_server_port` and `api_server_fallback_ports` the port.
- An argument to `from_config` wins over the file, which wins over the class, which wins over the default.
- A misspelt option, or a wrong value, stops the experiment with a message.

Next: [Build a config in the interface](setup_page.md), to write a config file from forms.

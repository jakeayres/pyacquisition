import tomllib
from .logging import logger
from ..instruments import instrument_map
from . import calculations


class TOMLConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


class UnexpectedSectionError(Exception):
    """Custom exception for unexpected sections in the configuration."""

    pass


class InvalidInstrumentError(Exception):
    """Custom exception for invalid instrument configurations."""

    pass


class InvalidMeasurementError(Exception):
    """Custom exception for invalid measurement configurations."""

    pass


class InvalidCalculationError(Exception):
    """A config's [calculations] section describes a calculation that can't be made."""

    pass


class InvalidTraceError(Exception):
    """A config's [traces] section describes a trace that can't be taken."""

    pass


# What an entry of [traces] may say.
TRACE_KEYS = {
    "instrument", "method", "every", "every_rows", "args", "unit", "x_unit",
    "reduce", "reduce_units", "channels", "timeout",
}


def _positive(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value > 0


def trace_problem(name: str, entry, instruments: dict) -> str | None:
    """What is wrong with an entry of [traces], or None."""
    from .trace_source import REDUCTIONS

    where = f"Trace '{name}'"
    if not isinstance(entry, dict):
        return f"{where} must be a table, such as {{instrument = \"vna\", method = \"get_sweep\"}}."
    unknown = sorted(set(entry) - TRACE_KEYS)
    if unknown:
        return f"{where} has {', '.join(map(repr, unknown))}, which a trace doesn't take."
    for key in ("instrument", "method"):
        if not isinstance(entry.get(key), str):
            return f"{where} needs `{key}`, as text."
    if entry["instrument"] not in instruments:
        return f"{where}: there is no instrument '{entry['instrument']}' in [instruments]."
    for key in ("every", "timeout"):
        if key in entry and not _positive(entry[key]):
            return f"{where}: `{key}` must be a number of seconds above 0."
    if "every_rows" in entry and (isinstance(entry["every_rows"], bool) or not isinstance(entry["every_rows"], int)
                                  or entry["every_rows"] < 1):
        return f"{where}: `every_rows` must be a whole number from 1."
    if "every" in entry and "every_rows" in entry:
        return f"{where}: give `every` or `every_rows`, not both."
    for key in ("unit", "x_unit"):
        if key in entry and not isinstance(entry[key], str):
            return f"{where}: `{key}` must be text, such as \"Hz\"."
    if "args" in entry and not isinstance(entry["args"], dict):
        return f"{where}: `args` must be a table of the method's inputs."
    if "reduce" in entry:
        reduce = entry["reduce"]
        if not isinstance(reduce, list) or not all(isinstance(r, str) for r in reduce):
            return f"{where}: `reduce` must be a list of reductions, such as [\"mean\", \"peak_x\"]."
        unknown = [r for r in reduce if r not in REDUCTIONS]
        if unknown:
            return f"{where}: there is no reduction {', '.join(map(repr, unknown))}; there are {', '.join(REDUCTIONS)}."
    if "reduce_units" in entry and not (
        isinstance(entry["reduce_units"], dict) and all(isinstance(u, str) for u in entry["reduce_units"].values())
    ):
        return f"{where}: `reduce_units` must be a table of units, such as {{mean = \"dB\"}}."
    if "channels" in entry and not (
        isinstance(entry["channels"], list) and entry["channels"] and all(isinstance(c, str) for c in entry["channels"])
    ):
        return f"{where}: `channels` must be a list of names."
    return None


class ConfigParser:
    ALLOWED_SECTIONS = [
        "experiment",
        "rack",
        "instruments",
        "measurements",
        "calculations",
        "traces",
        "data",
        "api_server",
        "logging",
        "gui",
    ]

    @staticmethod
    def parse(file_path: str) -> dict:
        """Parse a config. Delegate to appropriate parser based on file extension."""
        if file_path.endswith(".toml"):
            config = ConfigParser.load_toml(file_path)
        # elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
        #     with open(file_path, "r", encoding="utf-8") as file:
        #         return yaml.safe_load(file)
        else:
            raise TOMLConfigError(f"Unsupported file type: {file_path}")

        if ConfigParser.validate(config):
            logger.debug(f"Config validation passed for: {file_path}")
            return config
        else:
            logger.error(f"Config validation failed for: {file_path}")
            return config

    @staticmethod
    def load_toml(file_path: str) -> dict:
        """Load a TOML file."""
        try:
            with open(file_path, "rb") as file:
                config = tomllib.load(file)
                logger.debug(f"Loaded TOML config from {file_path}")
                return config
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Error decoding TOML file: {file_path}. Error: {e}")
            raise

    @staticmethod
    def validate(config: dict) -> None:
        if not ConfigParser.all_sections_are_valid(config):
            raise UnexpectedSectionError("Config contains unexpected sections.")
        if not ConfigParser.all_instrument_values_are_dicts(config):
            raise InvalidInstrumentError(
                "Config contains instrument entries that are not dictionaries."
            )
        if not ConfigParser.all_instrument_dicts_contain_instrument(config):
            raise InvalidInstrumentError(
                "Config contains instrument dictionaries that do not contain 'instrument' key."
            )
        if not ConfigParser.all_instruments_in_instrument_map(config):
            raise InvalidInstrumentError(
                "Config contains instruments that are not in the instrument map."
            )
        if not ConfigParser.all_measurement_values_are_dicts(config):
            raise InvalidMeasurementError(
                "Config contains measurement entries that are not dictionaries."
            )
        if not ConfigParser.all_measurement_dicts_contain_instrument(config):
            raise InvalidMeasurementError(
                "Config contains measurement dictionaries that do not contain 'instrument' key."
            )
        if not ConfigParser.all_measurement_instruments_exist(config):
            raise InvalidMeasurementError(
                "Config contains measurements with instruments that do not exist."
            )
        if not ConfigParser.all_measurement_units_are_text(config):
            raise InvalidMeasurementError(
                'Config contains a measurement whose unit is not text, such as "K".'
            )
        try:
            calculations.from_config(
                config.get("calculations", {}), config.get("measurements", {})
            )
        except ValueError as e:
            raise InvalidCalculationError(str(e)) from e
        for name, entry in config.get("traces", {}).items():
            problem = trace_problem(name, entry, config.get("instruments", {}))
            if problem:
                raise InvalidTraceError(problem)
        return config

    @staticmethod
    def all_sections_are_valid(config: dict) -> bool:
        """Check if all sections in the config are valid."""
        for section in config.keys():
            if section not in ConfigParser.ALLOWED_SECTIONS:
                logger.warning(f"Invalid section '{section}' found in config.")
                return False
        return True

    @staticmethod
    def all_instrument_values_are_dicts(config: dict) -> bool:
        """Check if all instrument values in the config are dictionaries."""
        for instrument, values in config.get("instruments", {}).items():
            if not isinstance(values, dict):
                logger.warning(
                    f"Instrument '{instrument}' does not have a dictionary value."
                )
                return False
        return True

    @staticmethod
    def all_instrument_dicts_contain_instrument(config: dict) -> bool:
        """Check if all instrument dictionaries contain the 'instrument' key."""
        for instrument, values in config.get("instruments", {}).items():
            if not isinstance(values, dict):
                logger.warning(
                    f"Instrument '{instrument}' does not have a dictionary value."
                )
                return False
            if "instrument" not in values:
                logger.warning(
                    f"Instrument '{instrument}' dictionary does not contain 'instrument' key."
                )
                return False
        return True

    @staticmethod
    def all_instruments_in_instrument_map(config: dict) -> bool:
        """Check if all instruments in the config are in the instrument map."""
        for instrument, values in config.get("instruments", {}).items():
            if values["instrument"] not in instrument_map.keys():
                logger.warning(
                    f"Instrument '{values['instrument']}' not found in instrument map."
                )
                return False
        return True

    @staticmethod
    def all_measurement_values_are_dicts(config: dict) -> bool:
        """Check if all measurements in the config are dictionaries."""
        for measurement, values in config.get("measurements", {}).items():
            if not isinstance(values, dict):
                logger.warning(
                    f"Measurement '{measurement}' does not have a dictionary value."
                )
                return False
        return True

    @staticmethod
    def all_measurement_dicts_contain_instrument(config: dict) -> bool:
        """Check if all measurement dictionaries contain the 'instrument' key."""
        for measurement, values in config.get("measurements", {}).items():
            if not isinstance(values, dict):
                logger.warning(
                    f"Measurement '{measurement}' does not have a dictionary value."
                )
                return False
            if "instrument" not in values:
                logger.warning(
                    f"Measurement '{measurement}' dictionary does not contain 'instrument' key."
                )
                return False
        return True

    @staticmethod
    def all_measurement_units_are_text(config: dict) -> bool:
        """Check that every measurement's unit, where one is given, is text."""
        for measurement, values in config.get("measurements", {}).items():
            if "unit" in values and not isinstance(values["unit"], str):
                logger.warning(
                    f"Measurement '{measurement}' has a unit that is not text: "
                    f"{values['unit']!r}."
                )
                return False
        return True

    @staticmethod
    def all_measurement_instruments_exist(config: dict) -> bool:
        """Check if all measurement instruments exist in the config."""
        for measurement, values in config.get("measurements", {}).items():
            inst = values["instrument"]
            if inst not in config.get("instruments", {}).keys():
                logger.warning(f"Instrument '{inst}' not found in instruments.")
                return False
        return True

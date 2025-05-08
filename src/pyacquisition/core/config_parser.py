import tomllib
from .logging import logger


class ConfigParser:

    
    ALLOWED_SECTIONS = ['experiment', 'instruments', 'measurements', 'data', 'api_server', 'logging', 'gui']

    @staticmethod
    def parse(file_path: str) -> dict:
        """Parse a config. Delegate to appropriate parser based on file extension."""
        if file_path.endswith(".toml"):
            config = ConfigParser.load_toml(file_path)
        # elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
        #     with open(file_path, "r", encoding="utf-8") as file:
        #         return yaml.safe_load(file)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")
        
        if ConfigParser.validate(config):
            logger.debug(f"Config validation passed for: {file_path}")
            return config
        else:
            logger.error(f"Config validation failed for: {file_path}")
            return config
        

    @staticmethod
    def load_toml(file_path: str) -> dict:
        """Load a TOML file."""
        with open(file_path, "rb") as file:
            config = tomllib.load(file)
        return config

    @staticmethod
    def validate(config: dict) -> None:
        
        if not ConfigParser.all_sections_are_valid(config):
            raise ValueError("Config contains invalid sections.")
        
        if not ConfigParser.all_instrument_values_are_dicts(config):
            raise ValueError("Config contains invalid instrument values.")#
        
        if not ConfigParser.all_instrument_dicts_contain_instrument(config):
            raise ValueError("Config contains instrument dictionaries without 'instrument' key.")
        
        
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
                logger.warning(f"Instrument '{instrument}' does not have a dictionary value.")
                return False
        return True

    @staticmethod
    def all_instrument_dicts_contain_instrument(config: dict) -> bool:
        """Check if all instrument dictionaries contain the 'instrument' key."""
        for instrument, values in config.get("instruments", {}).items():
            if not isinstance(values, dict):
                logger.warning(f"Instrument '{instrument}' does not have a dictionary value.")
                return False
            if "instrument" not in values:
                logger.warning(f"Instrument '{instrument}' dictionary does not contain 'instrument' key.")
                return False
        return True

    @staticmethod
    def all_measurement_instruments_exist(config: dict) -> bool:
        """Check if all measurement instruments exist in the config."""
        for measurement in config.get("measurements", {}):
            if "instrument" not in measurement:
                logger.warning(f"Measurement '{measurement}' does not have an 'instrument' key.")
                return False
            if measurement["instrument"] not in config.get("instruments", {}):
                logger.warning(f"Instrument '{measurement['instrument']}' not found in instruments.")
                return False
        return True


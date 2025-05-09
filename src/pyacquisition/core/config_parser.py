import tomllib
from .logging import logger
from ..instruments import instrument_map


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



class ConfigParser:

    
    ALLOWED_SECTIONS = ['experiment', 'rack', 'instruments', 'measurements', 'data', 'api_server', 'logging', 'gui']

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
            raise InvalidInstrumentError("Config contains instrument entries that are not dictionaries.")
        if not ConfigParser.all_instrument_dicts_contain_instrument(config):
            raise InvalidInstrumentError("Config contains instrument dictionaries that do not contain 'instrument' key.")
        if not ConfigParser.all_instruments_in_instrument_map(config):
            raise InvalidInstrumentError("Config contains instruments that are not in the instrument map.")
        if not ConfigParser.all_measurement_values_are_dicts(config):
            raise InvalidMeasurementError("Config contains measurement entries that are not dictionaries.")
        if not ConfigParser.all_measurement_dicts_contain_instrument(config):
            raise InvalidMeasurementError("Config contains measurement dictionaries that do not contain 'instrument' key.")
        if not ConfigParser.all_measurement_instruments_exist(config):
            raise InvalidMeasurementError("Config contains measurements with instruments that do not exist.")
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
    def all_instruments_in_instrument_map(config: dict) -> bool:
        """Check if all instruments in the config are in the instrument map."""
        for instrument, values in config.get("instruments", {}).items():
            if values["instrument"] not in instrument_map.keys():
                logger.warning(f"Instrument '{values['instrument']}' not found in instrument map.")
                return False
        return True
    
    
    @staticmethod
    def all_measurement_values_are_dicts(config: dict) -> bool:
        """Check if all measurements in the config are dictionaries."""
        for measurement, values in config.get("measurements", {}).items():
            if not isinstance(values, dict):
                logger.warning(f"Measurement '{measurement}' does not have a dictionary value.")
                return False
        return True
    
    
    @staticmethod
    def all_measurement_dicts_contain_instrument(config: dict) -> bool:
        """Check if all measurement dictionaries contain the 'instrument' key."""
        for measurement, values in config.get("measurements", {}).items():
            if not isinstance(values, dict):
                logger.warning(f"Measurement '{measurement}' does not have a dictionary value.")
                return False
            if "instrument" not in values:
                logger.warning(f"Measurement '{measurement}' dictionary does not contain 'instrument' key.")
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


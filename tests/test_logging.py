import os
import pytest
from pyacquisition.core.logging import Logger

@pytest.fixture
def logger_instance():
    """Fixture to provide a fresh instance of the Logger singleton."""
    logger = Logger()
    yield logger

@pytest.fixture
def temp_log_dir(tmp_path_factory):
    """Fixture to provide a temporary directory for log files that gets cleaned up."""
    temp_dir = tmp_path_factory.mktemp("logs")
    yield temp_dir
    # Cleanup is handled automatically by pytest

def test_logger_singleton(logger_instance):
    """Test that Logger is a singleton."""
    logger1 = logger_instance
    logger2 = Logger()
    assert logger1 is logger2, "Logger is not a singleton"

def test_logger_initialization(logger_instance):
    """Test that Logger initializes correctly."""
    assert hasattr(logger_instance, "_initialized"), "Logger is not initialized"
    assert logger_instance._initialized is True, "Logger initialization flag is incorrect"

def test_logger_configuration(temp_log_dir, logger_instance):
    """Test that Logger configures logging correctly."""
    log_file_name = "test_debug.log"
    logger_instance.configure(
        root_path=temp_log_dir,
        console_level="INFO",
        file_level="WARNING",
        file_name=log_file_name,
    )
    
    # Check if the log file is created
    log_file_path = os.path.join(temp_log_dir, log_file_name)
    assert os.path.exists(log_file_path), "Log file was not created"

    # Check if the logger is configured (loguru doesn't expose internal state, so we rely on file creation)
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()
        assert log_contents == "", "Log file should be empty initially"

def test_logger_debug(temp_log_dir, logger_instance):
    """Test that Logger logs debug messages correctly."""
    log_file_name = "test_debug.log"
    logger_instance.configure(
        root_path=temp_log_dir,
        console_level="DEBUG",
        file_level="DEBUG",
        file_name=log_file_name,
    )
    
    logger_instance.debug("This is a debug message")
    
    log_file_path = os.path.join(temp_log_dir, log_file_name)
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()
        assert "This is a debug message" in log_contents, "Debug message was not logged"

def test_logger_info(temp_log_dir, logger_instance):
    """Test that Logger logs info messages correctly."""
    log_file_name = "test_info.log"
    logger_instance.configure(
        root_path=temp_log_dir,
        console_level="INFO",
        file_level="INFO",
        file_name=log_file_name,
    )
    
    logger_instance.info("This is an info message")
    
    log_file_path = os.path.join(temp_log_dir, log_file_name)
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()
        assert "This is an info message" in log_contents, "Info message was not logged"
        
        
def test_logger_debug_when_info(temp_log_dir, logger_instance):
    """ Test that the debugger does not log debug messages when the console level is set to INFO """
    log_file_name = "test_debug_when_info.log"
    logger_instance.configure(
        root_path=temp_log_dir,
        console_level="INFO",
        file_level="INFO",
        file_name=log_file_name,
    )
    
    logger_instance.debug("This is a debug message")
    
    log_file_path = os.path.join(temp_log_dir, log_file_name)
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()
        assert "This is a debug message" not in log_contents, "Debug message was logged when it shouldn't have been"

def test_logger_warning(temp_log_dir, logger_instance):
    """Test that Logger logs warning messages correctly."""
    log_file_name = "test_warning.log"
    logger_instance.configure(
        root_path=temp_log_dir,
        console_level="WARNING",
        file_level="WARNING",
        file_name=log_file_name,
    )
    
    logger_instance.warning("This is a warning message")
    
    log_file_path = os.path.join(temp_log_dir, log_file_name)
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()
        assert "This is a warning message" in log_contents, "Warning message was not logged"

def test_logger_error(temp_log_dir, logger_instance):
    """Test that Logger logs error messages correctly."""
    log_file_name = "test_error.log"
    logger_instance.configure(
        root_path=temp_log_dir,
        console_level="ERROR",
        file_level="ERROR",
        file_name=log_file_name,
    )
    
    logger_instance.error("This is an error message")
    
    log_file_path = os.path.join(temp_log_dir, log_file_name)
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()
        assert "This is an error message" in log_contents, "Error message was not logged"

def test_logger_exception(temp_log_dir, logger_instance):
    """Test that Logger logs exception messages correctly."""
    log_file_name = "test_exception.log"
    logger_instance.configure(
        root_path=temp_log_dir,
        console_level="ERROR",
        file_level="ERROR",
        file_name=log_file_name,
    )
    
    try:
        raise ValueError("This is a test exception")
    except ValueError:
        logger_instance.exception("An exception occurred")
    
    log_file_path = os.path.join(temp_log_dir, log_file_name)
    with open(log_file_path, "r") as log_file:
        log_contents = log_file.read()
        assert "An exception occurred" in log_contents, "Exception message was not logged"
        assert "ValueError: This is a test exception" in log_contents, "Exception details were not logged"
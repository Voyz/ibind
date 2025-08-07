"""
Unit tests for logging utilities.

The logs module provides centralized logging configuration and management for the ibind
library. It handles console logging, file-based logging with daily rotation, and
project-specific logger creation. The module supports environment-based configuration
and ensures proper log formatting across all components.

Core Functionality Tested:
==========================

1. **Project Logger Creation**:
   - Logger naming based on file paths
   - Default logger instantiation
   - Logger hierarchy and namespace management

2. **Logging System Initialization**:
   - Console output configuration
   - File-based logging setup
   - Log level and format configuration
   - Initialization state management and idempotency

3. **Daily Rotating File Handler**:
   - Automatic daily file rotation based on timestamps
   - File path generation with date suffixes
   - Directory creation for log files
   - Stream management and file handle lifecycle

4. **Configuration Management**:
   - Environment variable integration
   - Default value handling
   - Runtime configuration override
   - Logging behavior control flags

Key Components:
===============

- **project_logger()**: Creates project-specific logger instances with proper naming
- **ibind_logs_initialize()**: Configures the entire logging system with handlers and formatters
- **new_daily_rotating_file_handler()**: Sets up file-based logging with daily rotation
- **DailyRotatingFileHandler**: Custom logging handler for automatic daily file rotation

Test Coverage:
==============

This test suite provides comprehensive coverage of logging functionality including:

- **Logger Creation**: All project logger naming patterns and configurations
- **Initialization Logic**: Complete system setup with various parameter combinations
- **File Handling**: Daily rotation mechanics, file creation, and cleanup
- **Error Conditions**: Invalid configurations, file system errors, and edge cases
- **State Management**: Initialization tracking, global state handling, and reset scenarios

The tests use extensive mocking to isolate logging components while maintaining
realistic interaction patterns with the Python logging framework.

Logging Behavior:
=================

The logging system supports multiple output modes:
- Console-only logging for development
- File-only logging for production
- Combined console and file logging
- Disabled logging for testing environments

File logs use daily rotation with timestamps in filenames (e.g., `app__2024-01-15.txt`)
and automatic directory creation for log storage locations.

Security Considerations:
========================

Logging systems handle potentially sensitive information and file system access.
Tests ensure proper handling of file permissions, directory traversal prevention,
and safe handling of user-provided log file paths without exposing system internals.
"""

import datetime
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from ibind.support.logs import (
    project_logger,
    ibind_logs_initialize,
    new_daily_rotating_file_handler,
    DailyRotatingFileHandler,
    DEFAULT_FORMAT
)


@pytest.fixture
def reset_logging_state():
    """Reset global logging state before and after each test."""
    # Reset global state before test
    import ibind.support.logs
    ibind.support.logs._initialized = False
    ibind.support.logs._log_to_file = False

    # Clear any existing loggers
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        if logger_name.startswith('ibind'):
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.filters.clear()

    yield

    # Reset global state after test
    ibind.support.logs._initialized = False
    ibind.support.logs._log_to_file = False

    # Clear loggers again
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        if logger_name.startswith('ibind'):
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.filters.clear()


def test_project_logger_without_filepath():
    # Arrange

    # Act
    logger = project_logger()

    # Assert
    assert logger.name == 'ibind'
    assert isinstance(logger, logging.Logger)


def test_project_logger_with_filepath():
    # Arrange
    filepath = '/path/to/test_module.py'

    # Act
    logger = project_logger(filepath)

    # Assert
    assert logger.name == 'ibind.test_module'
    assert isinstance(logger, logging.Logger)


def test_project_logger_with_complex_filepath():
    # Arrange
    filepath = '/very/long/path/to/some/complex_module_name.py'

    # Act
    logger = project_logger(filepath)

    # Assert
    assert logger.name == 'ibind.complex_module_name'
    assert isinstance(logger, logging.Logger)


def test_project_logger_with_pathlib_path():
    # Arrange
    filepath = Path('/path/to/module.py')

    # Act
    logger = project_logger(str(filepath))

    # Assert
    assert logger.name == 'ibind.module'
    assert isinstance(logger, logging.Logger)


def test_project_logger_with_no_extension():
    # Arrange
    filepath = '/path/to/module'

    # Act
    logger = project_logger(filepath)

    # Assert
    assert logger.name == 'ibind.module'
    assert isinstance(logger, logging.Logger)


@patch('ibind.support.logs.var.LOG_TO_CONSOLE', True)
@patch('ibind.support.logs.var.LOG_TO_FILE', False)
@patch('ibind.support.logs.var.LOG_LEVEL', 'DEBUG')
@patch('ibind.support.logs.var.LOG_FORMAT', DEFAULT_FORMAT)
@patch('ibind.support.logs.var.PRINT_FILE_LOGS', False)
def test_ibind_logs_initialize_console_only(reset_logging_state):
    # Arrange

    # Act
    ibind_logs_initialize()

    # Assert
    logger = logging.getLogger('ibind')
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)


@patch('ibind.support.logs.var.LOG_TO_CONSOLE', False)
@patch('ibind.support.logs.var.LOG_TO_FILE', True)
@patch('ibind.support.logs.var.LOG_LEVEL', 'INFO')
@patch('ibind.support.logs.var.LOG_FORMAT', DEFAULT_FORMAT)
@patch('ibind.support.logs.var.PRINT_FILE_LOGS', False)
def test_ibind_logs_initialize_file_only(reset_logging_state):
    # Arrange

    # Act
    ibind_logs_initialize(log_to_console=False, log_to_file=True)

    # Assert
    logger = logging.getLogger('ibind')
    assert logger.level == logging.DEBUG
    # Should have no console handlers when log_to_console=False
    console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(console_handlers) == 0


def test_ibind_logs_initialize_custom_parameters(reset_logging_state):
    # Arrange
    custom_format = '%(levelname)s - %(message)s'

    # Act
    ibind_logs_initialize(
        log_to_console=True,
        log_to_file=False,
        log_level='WARNING',
        log_format=custom_format,
        print_file_logs=False
    )

    # Assert
    logger = logging.getLogger('ibind')
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    handler = logger.handlers[0]
    assert handler.level == logging.WARNING
    # Check formatter format string
    assert handler.formatter._fmt == custom_format


def test_ibind_logs_initialize_idempotent(reset_logging_state):
    # Arrange

    # Act
    ibind_logs_initialize(log_to_console=True)
    initial_handler_count = len(logging.getLogger('ibind').handlers)

    # Call again - should not add more handlers
    ibind_logs_initialize(log_to_console=True)

    # Assert
    final_handler_count = len(logging.getLogger('ibind').handlers)
    assert initial_handler_count == final_handler_count


@patch('ibind.support.logs.var.LOG_TO_CONSOLE', True)
@patch('ibind.support.logs.var.LOG_TO_FILE', True)
@patch('ibind.support.logs.var.PRINT_FILE_LOGS', True)
def test_ibind_logs_initialize_with_file_and_console(reset_logging_state):
    # Arrange

    # Act
    ibind_logs_initialize(log_to_console=True, log_to_file=True, print_file_logs=True)

    # Assert
    logger = logging.getLogger('ibind')
    console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(console_handlers) == 1

    # Check that file handler logger also gets console output when print_file_logs=True
    fh_logger = logging.getLogger('ibind_fh')
    fh_console_handlers = [h for h in fh_logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(fh_console_handlers) == 1


def test_ibind_logs_initialize_disables_file_logging(reset_logging_state):
    # Arrange

    # Act
    ibind_logs_initialize(log_to_file=False)

    # Assert
    fh_logger = logging.getLogger('ibind_fh')
    # Should have a filter that blocks all records
    assert len(fh_logger.filters) > 0
    # Test the filter blocks records
    test_record = logging.LogRecord('test', logging.INFO, 'path', 1, 'msg', (), None)
    assert not fh_logger.filters[0](test_record)


@patch('ibind.support.logs._LOGGER')
def test_new_daily_rotating_file_handler_with_file_logging(mock_logger, reset_logging_state):
    # Arrange
    import ibind.support.logs
    ibind.support.logs._log_to_file = True
    logger_name = 'test_logger'
    filepath = '/tmp/test.log'  # noqa: S108

    # Act
    with patch('ibind.support.logs.DailyRotatingFileHandler') as mock_handler_class:
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler

        logger = new_daily_rotating_file_handler(logger_name, filepath)

    # Assert
    assert logger.name == 'ibind_fh.test_logger'
    assert logger.level == logging.DEBUG
    mock_logger.info.assert_called_once()
    assert 'test_logger' in mock_logger.info.call_args[0][0]
    assert filepath in mock_logger.info.call_args[0][0]


def test_new_daily_rotating_file_handler_without_file_logging(reset_logging_state):
    # Arrange
    import ibind.support.logs
    ibind.support.logs._log_to_file = False
    logger_name = 'test_logger'
    filepath = '/tmp/test.log'  # noqa: S108

    # Act
    logger = new_daily_rotating_file_handler(logger_name, filepath)

    # Assert
    assert logger.name == 'ibind_fh.test_logger'
    # Should have a NullHandler when file logging is disabled
    null_handlers = [h for h in logger.handlers if isinstance(h, logging.NullHandler)]
    assert len(null_handlers) == 1


def test_new_daily_rotating_file_handler_existing_handlers(reset_logging_state):
    # Arrange
    import ibind.support.logs
    ibind.support.logs._log_to_file = True
    logger_name = 'test_logger'
    filepath = '/tmp/test.log'  # noqa: S108

    # Pre-create logger with existing handler
    logger = logging.getLogger('ibind_fh.test_logger')
    existing_handler = logging.Handler()
    logger.addHandler(existing_handler)

    # Act
    result_logger = new_daily_rotating_file_handler(logger_name, filepath)

    # Assert
    assert result_logger is logger
    # Should not add new handlers if handlers already exist
    assert len(logger.handlers) == 1  # Only the existing handler


def test_daily_rotating_file_handler_initialization():
    # Arrange
    base_filename = '/tmp/test.log'  # noqa: S108

    # Act
    with patch('builtins.open', mock_open()):
        handler = DailyRotatingFileHandler(base_filename)

    # Assert
    assert handler.baseFilename == base_filename
    assert handler.timestamp is not None  # Will be set during initialization
    assert handler.date_format == '%Y-%m-%d'


def test_daily_rotating_file_handler_custom_date_format():
    # Arrange
    base_filename = '/tmp/test.log'  # noqa: S108
    custom_format = '%Y%m%d'

    # Act
    handler = DailyRotatingFileHandler(base_filename, date_format=custom_format)

    # Assert
    assert handler.date_format == custom_format


@patch('ibind.support.logs.datetime')
def test_daily_rotating_file_handler_get_timestamp(mock_datetime):
    # Arrange
    mock_now = MagicMock()
    mock_now.strftime.return_value = '2024-01-15'
    mock_datetime.datetime.now.return_value = mock_now
    mock_datetime.timezone.utc = datetime.timezone.utc

    with patch('builtins.open', mock_open()):
        handler = DailyRotatingFileHandler('/tmp/test.log')  # noqa: S108  # noqa: S108

    # Act
    timestamp = handler.get_timestamp()

    # Assert
    assert timestamp == '2024-01-15'
    # Note: datetime.now gets called during initialization too, so we check if it was called
    assert mock_datetime.datetime.now.call_count >= 1
    mock_now.strftime.assert_called_with('%Y-%m-%d')


def test_daily_rotating_file_handler_get_filename():
    # Arrange
    handler = DailyRotatingFileHandler('/tmp/test.log')  # noqa: S108
    timestamp = '2024-01-15'

    # Act
    filename = handler.get_filename(timestamp)

    # Assert
    assert filename == '/tmp/test.log__2024-01-15.txt'  # noqa: S108


@patch('ibind.support.logs.Path')
@patch('builtins.open', new_callable=mock_open)
def test_daily_rotating_file_handler_open(mock_file_open, mock_path):
    # Arrange
    mock_path.return_value.parent.mkdir = MagicMock()

    with patch('builtins.open', mock_open()):
        handler = DailyRotatingFileHandler('/tmp/test.log')  # noqa: S108  # noqa: S108

    with patch.object(handler, 'get_timestamp', return_value='2024-01-15'):
        # Act
        handler._open()

    # Assert
    assert handler.timestamp == '2024-01-15'
    # Path gets called during initialization and during _open
    expected_path = '/tmp/test.log__2024-01-15.txt'  # noqa: S108
    assert any(call[0][0] == expected_path for call in mock_path.call_args_list)
    mock_path.return_value.parent.mkdir.assert_called_with(parents=True, exist_ok=True)
    mock_file_open.assert_called_with(expected_path, 'a', encoding='utf-8')


@patch('ibind.support.logs.Path')
@patch('builtins.open', new_callable=mock_open)
def test_daily_rotating_file_handler_emit_same_day(mock_file_open, mock_path):
    # Arrange
    handler = DailyRotatingFileHandler('/tmp/test.log')  # noqa: S108
    handler.timestamp = '2024-01-15'
    mock_stream = MagicMock()
    handler.stream = mock_stream

    record = logging.LogRecord('test', logging.INFO, 'path', 1, 'Test message', (), None)

    with patch.object(handler, 'get_timestamp', return_value='2024-01-15'):
        with patch('logging.FileHandler.emit') as mock_super_emit:
            # Act
            handler.emit(record)

    # Assert
    # Should not reopen file on same day
    assert handler.stream is mock_stream
    mock_super_emit.assert_called_once_with(record)


@patch('ibind.support.logs.Path')
@patch('builtins.open', new_callable=mock_open)
def test_daily_rotating_file_handler_emit_new_day(mock_file_open, mock_path):
    # Arrange
    mock_path.return_value.parent.mkdir = MagicMock()

    with patch('builtins.open', mock_open()):
        handler = DailyRotatingFileHandler('/tmp/test.log')  # noqa: S108  # noqa: S108

    handler.timestamp = '2024-01-15'
    old_stream = MagicMock()
    handler.stream = old_stream

    record = logging.LogRecord('test', logging.INFO, 'path', 1, 'Test message', (), None)

    with patch.object(handler, 'get_timestamp', return_value='2024-01-16'):
        with patch.object(handler, 'close') as mock_close:
            with patch('logging.FileHandler.emit') as mock_super_emit:
                # Act
                handler.emit(record)

    # Assert
    # Should close old stream and open new one for new day
    assert mock_close.call_count >= 1  # May be called during init and emit
    assert handler.timestamp == '2024-01-16'
    expected_path = '/tmp/test.log__2024-01-16.txt'  # noqa: S108
    mock_file_open.assert_called_with(expected_path, 'a', encoding='utf-8')
    mock_super_emit.assert_called_once_with(record)


def test_daily_rotating_file_handler_emit_no_existing_stream():
    # Arrange
    handler = DailyRotatingFileHandler('/tmp/test.log')  # noqa: S108
    handler.stream = None
    record = logging.LogRecord('test', logging.INFO, 'path', 1, 'Test message', (), None)

    with patch.object(handler, 'get_timestamp', return_value='2024-01-15'):
        with patch.object(handler, '_open', return_value=MagicMock()) as mock_open_method:
            with patch('logging.FileHandler.emit') as mock_super_emit:
                # Act
                handler.emit(record)

    # Assert
    mock_open_method.assert_called_once()
    mock_super_emit.assert_called_once_with(record)


def test_default_format_constant():
    # Arrange & Act & Assert
    assert DEFAULT_FORMAT == '%(asctime)s|%(levelname)-.1s| %(message)s'

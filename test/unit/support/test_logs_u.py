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


def test_new_daily_rotating_file_handler_with_file_logging(reset_logging_state):
    # Arrange
    import ibind.support.logs
    ibind.support.logs._log_to_file = True
    logger_name = 'test_logger'
    filepath = '/tmp/test.log'  # noqa: S108

    # Mock only file operations, not the handler itself
    with patch('builtins.open', mock_open()), \
         patch('ibind.support.logs.Path') as mock_path:
        mock_path.return_value.parent.mkdir = MagicMock()

        # Act - Test real DailyRotatingFileHandler behavior
        logger = new_daily_rotating_file_handler(logger_name, filepath)

    # Assert
    assert logger.name == 'ibind_fh.test_logger'
    assert logger.level == logging.DEBUG
    # Verify logger has real DailyRotatingFileHandler
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], DailyRotatingFileHandler)
    assert logger.handlers[0].baseFilename == filepath


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


def test_daily_rotating_file_handler_open():
    # Arrange
    base_filename = '/tmp/test.log'  # noqa: S108

    # Mock only file operations and Path.mkdir, not the entire Path class
    with patch('builtins.open', mock_open()) as mock_file_open, \
         patch('pathlib.Path.mkdir') as mock_mkdir:
        
        handler = DailyRotatingFileHandler(base_filename)
        
        # Test real get_timestamp behavior by using a fixed date
        with patch.object(handler, 'get_timestamp', return_value='2024-01-15'):
            # Act - Test real _open behavior
            file_obj = handler._open()

    # Assert
    assert handler.timestamp == '2024-01-15'
    expected_path = '/tmp/test.log__2024-01-15.txt'  # noqa: S108
    
    # Verify real get_filename behavior was used
    assert handler.get_filename('2024-01-15') == expected_path
    
    # Verify directory creation and file opening
    mock_mkdir.assert_called_with(parents=True, exist_ok=True)
    mock_file_open.assert_called_with(expected_path, 'a', encoding='utf-8')


def test_daily_rotating_file_handler_emit_rotation():
    # Arrange
    base_filename = '/tmp/test.log'  # noqa: S108
    
    with patch('builtins.open', mock_open()) as mock_file_open, \
         patch('pathlib.Path.mkdir') as mock_mkdir:
        
        handler = DailyRotatingFileHandler(base_filename)
        handler.timestamp = '2024-01-15'  # Set initial timestamp
        
        # Create a mock stream to simulate file being open
        mock_stream = MagicMock()
        handler.stream = mock_stream
        
        # Create test log record
        record = logging.LogRecord('test', logging.INFO, 'path', 1, 'test message', (), None)
        
        # Test case 1: Same timestamp - no rotation
        with patch.object(handler, 'get_timestamp', return_value='2024-01-15'):
            handler.emit(record)
        
        # Should not have called close or _open
        mock_stream.close.assert_not_called()
        
        # Test case 2: Different timestamp - should rotate
        with patch.object(handler, 'get_timestamp', return_value='2024-01-16'), \
             patch.object(handler, '_open', return_value=MagicMock()) as mock_open_method:
            
            handler.emit(record)
        
        # Should have closed old file and opened new one
        mock_stream.close.assert_called_once()
        mock_open_method.assert_called_once()


def test_default_format_constant():
    # Arrange & Act & Assert
    assert DEFAULT_FORMAT == '%(asctime)s|%(levelname)-.1s| %(message)s'

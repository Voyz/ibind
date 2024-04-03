import datetime
import logging
import sys
from pathlib import Path

import var

DEFAULT_FORMAT = '%(asctime)s|%(levelname)-.1s| %(message)s'

_initialized = False
_log_to_file = False


def project_logger(filepath=None):
    """
    Returns a project-specific logger instance.

    This function creates a new logger instance with the name `'ibind'.{filepath.stem}` if `filepath` is specified,
    or 'ibind' if `filepath` is not specified.

    Parameters:
        filepath (str): The file path where the log files will be stored. If no filepath is specified, the default logs directory will be used.

    Returns:
        logging.Logger: The project-specific logger instance.
    """
    return logging.getLogger('ibind' + (f'.{Path(filepath).stem}' if filepath is not None else ''))

_LOGGER = project_logger()

def initialize(
        log_to_console: bool = var.LOG_TO_CONSOLE,
        log_format: str = var.LOG_FORMAT,
        log_level: str = var.LOG_LEVEL,
        log_to_file: bool = var.LOG_TO_FILE,
):
    global _initialized
    if _initialized: return
    _initialized = True

    global _log_to_file
    _log_to_file = log_to_file


    logger = logging.getLogger('ibind')
    formatter = logging.Formatter(log_format)
    logger.setLevel(logging.DEBUG)

    if log_to_console:
        # stdout handler, for INFO and below:
        h1 = logging.StreamHandler(stream=sys.stdout)
        h1.setLevel(getattr(logging, log_level))
        h1.addFilter(lambda record: record.levelno <= logging.INFO)
        h1.setFormatter(formatter)
        logger.addHandler(h1)

    # stderr handler, for WARNING and above:
    h2 = logging.StreamHandler(stream=sys.stderr)
    h2.setLevel(logging.WARNING)
    h2.setFormatter(formatter)
    logger.addHandler(h2)

    if not _log_to_file:
        logging.getLogger('ibind_fh').addFilter(lambda record: False)


def new_daily_rotating_file_handler(logger_name, filepath):
    """
    Creates and configures a new daily rotating file handler for logging.

    This function sets up a file-based logger with a daily rotation. It ensures that each day's logs are
    saved in a separate file. The logger is configured with a specific name and file path. If the logger
    with the given name doesn't already have handlers, it adds a new daily rotating file handler to it.

    Parameters:
        logger_name (str): The name to be assigned to the logger. This name is used to identify the logger instance.
        filepath (str): The file path where the log files will be stored. This path determines the location of the log files.

    Returns:
        logging.Logger: The logger configured with the daily rotating file handler.

    Note:
        - The logger is set to DEBUG level by default.
        - The format of the logs is determined by the DEFAULT_FORMAT global variable.
    """
    logger = logging.getLogger(f'ibind_fh.{logger_name}')

    if _log_to_file:
        _LOGGER.info(f'New daily rotating file handler for logger "{logger_name}": {filepath}')
        if len(logger.handlers) == 0:
            fh_logger = logging.getLogger('ibind_fh')
            handler = DailyRotatingFileHandler(filepath, encoding='utf-8')
            handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))

            # if filehandler outputs are disabled, this should bring over the filter that will do this
            for filter in fh_logger.filters:
                logger.addFilter(filter)
            logger.addHandler(handler)

        logger.setLevel(logging.DEBUG)
    else:
        logger.addHandler(logging.NullHandler())

    return logger


class DailyRotatingFileHandler(logging.FileHandler):

    def __init__(self, *args, date_format='%Y-%m-%d', **kwargs):
        self.timestamp = None
        self.date_format = date_format
        self.stream = None
        super().__init__(*args, **kwargs)

    def get_timestamp(self):
        now = datetime.datetime.now(datetime.UTC)
        return now.strftime(self.date_format)

    def get_filename(self, timestamp):
        return f'{self.baseFilename}__{timestamp}.txt'

    def _open(self):
        if self.stream is not None:
            self.close()
        self.timestamp = self.get_timestamp()
        filename = self.get_filename(self.timestamp)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        return open(filename, self.mode, encoding='utf-8')

    def emit(self, record):
        if self.get_timestamp() != self.timestamp:
            self.close()
            self.stream = self._open()

        super().emit(record)


import inspect
import logging

from loguru import logger

loggers = ("apscheduler.*",)


class InterceptHandler(logging.Handler):
    """Recommended intercept handler for loguru

    Args:
        record: The logging record to emit
    """

    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def propagate_logs() -> None:
    """Propogates the stdlib loggers to the loguru logger"""

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = []
        logging_logger.propagate = True

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

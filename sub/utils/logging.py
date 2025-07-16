# utils/logging.py
import logging
import sys


class Colour:
    """Class to provide ANSI escape codes for colors."""
    def __init__(self):
        self._codes = {
            'blue': '\033[94m',    # Blue
            'green': '\033[92m',   # Green
            'yellow': '\033[93m',  # Yellow
            'red': '\033[91m',     # Red
            'magenta': '\033[95m', # Magenta
            'reset': '\033[0m',    # Reset
        }
    @property
    def blue(self):
        return self._codes['blue']

    @property
    def green(self):
        return self._codes['green']

    @property
    def yellow(self):
        return self._codes['yellow']

    @property
    def red(self):
        return self._codes['red']

    @property
    def magenta(self):
        return self._codes['magenta']

    @property
    def reset(self):
        return self._codes['reset']
colour = Colour()

class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: colour.blue,
        logging.INFO: colour.green,
        logging.WARNING: colour.yellow,
        logging.ERROR: colour.red,
        logging.CRITICAL: colour.magenta,
    }

    
    def format(self, record):
        level_color = self.LEVEL_COLORS.get(record.levelno, colour.reset)
        reset = colour.reset

        # Color log level
        record.levelname = f"{level_color}{record.levelname}{reset}"

        return super().format(record)


def setup_logger(name: str = "network_scanner") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        return logger  # prevent duplicate handlers

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    # Format
    formatter = ColorFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

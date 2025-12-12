import logging
import os
import sys
from functools import cache, wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Awaitable, Callable, ParamSpec, TypeVar

from dotenv import load_dotenv
from platformdirs import user_log_dir, user_log_path

from matlab_simulink_mcp import get_package_name

P = ParamSpec("P")
R = TypeVar("R")


@cache
def get_logger(env_key: str = "LOG_DIR") -> logging.Logger:
    load_dotenv()

    name = get_package_name()
    dir = Path(os.environ[env_key]) if env_key in os.environ else Path(user_log_dir(name))

    filepath = Path(name).with_suffix(".log")
    if dir:
        try:
            dir = Path(dir)
            dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            dir = user_log_path(filepath.stem, appauthor=False)
            dir.mkdir(parents=True, exist_ok=True)
    filepath = dir / filepath

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = RotatingFileHandler(filepath, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


def log_error(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            get_logger().exception(e)
            raise e

    return wrapper

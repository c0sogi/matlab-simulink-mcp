import logging
import os
import sys
import types
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Generic, TypeVar

import matlab.engine  # pyright: ignore[reportMissingTypeStubs]
from dotenv import load_dotenv
from fastmcp.exceptions import ToolError

import matlab_simulink_mcp
from matlab_simulink_mcp.utils.logging import (
    TrailingConsole,
    create_console,
    create_log_file,
    create_logger,
)

_T = TypeVar("_T")


class Singleton(type, Generic[_T]):
    _instances: dict["Singleton[_T]", _T] = {}

    def __call__(cls, *args: object, **kwargs: object) -> _T:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass
class MatlabEngine(metaclass=Singleton["MatlabEngine"]):
    """Singleton for holding MATLAB engine"""

    @property
    def helpers(self) -> Path:
        helper_path = Path("helpers")

        if getattr(sys, "frozen", False):
            base_path = Path(getattr(sys, "_MEIPASS")) / "matlab_simulink_mcp"
            return base_path / helper_path

        return get_full_path(matlab_simulink_mcp, helper_path)

    @cached_property
    def engine(self) -> matlab.engine.MatlabEngine:
        if sessions := matlab.engine.find_matlab():
            eng = matlab.engine.connect_matlab(sessions[0])  # pyright: ignore[reportUnknownMemberType]
            assert isinstance(eng, matlab.engine.MatlabEngine), (
                f"Connected MATLAB engine is not of type MatlabEngine: {type(eng)}"
            )
        else:
            eng = matlab.engine.start_matlab()  # pyright: ignore[reportUnknownMemberType]
            assert isinstance(eng, matlab.engine.MatlabEngine), (
                f"Started MATLAB engine is not of type MatlabEngine: {type(eng)}"
            )

        #  Add helpers to MATLAB path once
        eng.addpath(str(self.helpers), nargout=0)
        return eng

    @cached_property
    def log_file(self) -> Path:
        load_dotenv()
        return create_log_file(
            filename=matlab_simulink_mcp.__name__,
            dir=get_full_path(matlab_simulink_mcp, Path(os.getenv("LOG_DIR", "."))),
        )

    @cached_property
    def log_console(self) -> TrailingConsole:
        return create_console(log_file=self.log_file)

    @cached_property
    def logger(self) -> logging.Logger:
        return create_logger(name=matlab_simulink_mcp.__name__, log_file=self.log_file)


def get_full_path(pkg: types.ModuleType, path: Path) -> Path:
    """Absolutizes a path relative to a given package. Returns as is if already absolute"""
    if path.is_absolute():
        return path
    pkg_file = pkg.__file__
    if pkg_file is None:
        raise ToolError("Package file not found")
    return (Path(pkg_file).resolve().parent / path).resolve()

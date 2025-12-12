from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import cached_property
from importlib.resources import as_file, files
from pathlib import Path
from typing import Generic, TypeVar

import matlab.engine  # pyright: ignore[reportMissingTypeStubs]
from fastmcp.exceptions import ToolError

from matlab_simulink_mcp.utils.logging import get_logger
from matlab_simulink_mcp import get_package_name

_T = TypeVar("_T")


class Singleton(type, Generic[_T]):
    _instances: dict["Singleton[_T]", _T] = {}

    def __call__(cls, *args: object, **kwargs: object) -> _T:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass
class MatlabEngine(metaclass=Singleton["MatlabEngine"]):
    """
    Singleton for holding MATLAB engine.

    Ensures that helper .m files packaged inside the Python package
    remain available on disk for the entire lifetime of the MATLAB engine,
    even under PyInstaller one-file / zipimport environments.
    """

    _resource_stack: ExitStack = field(default_factory=ExitStack, init=False)
    _helpers_dir: Path | None = field(default=None, init=False)

    def _get_helpers_dir(self) -> Path:
        """
        Materialize (if needed) and return the helpers directory as a real
        filesystem path whose lifetime is bound to this MatlabEngine instance.
        """
        if self._helpers_dir is not None:
            return self._helpers_dir

        # helpers is located at: package_root / "helpers"
        helpers_resource = files(get_package_name()) / "helpers"

        # Keep the as_file() context alive for the lifetime of this object
        helpers_dir = self._resource_stack.enter_context(as_file(helpers_resource))

        if not helpers_dir.exists():
            raise ToolError(f"MATLAB helper directory not found: {helpers_dir}")

        self._helpers_dir = helpers_dir
        return helpers_dir

    @cached_property
    def engine(self) -> matlab.engine.MatlabEngine:
        """
        Start or connect to a MATLAB engine and ensure helper paths are added.
        """
        logger = get_logger()

        # Connect to existing session or start a new one
        sessions = matlab.engine.find_matlab()
        if sessions:
            eng = matlab.engine.connect_matlab(sessions[0])  # pyright: ignore[reportUnknownMemberType]
            logger.info(f"Connected to existing MATLAB session: {sessions[0]}")
        else:
            eng = matlab.engine.start_matlab()  # pyright: ignore[reportUnknownMemberType]
            logger.info("Started new MATLAB session")

        if not isinstance(eng, matlab.engine.MatlabEngine):
            raise ToolError(f"MATLAB engine is not MatlabEngine: {type(eng)}")

        # Prepare helpers directory (guaranteed to stay alive)
        helpers_dir = self._get_helpers_dir()

        logger.info(f"Adding helpers to MATLAB path: {helpers_dir}")
        helper_root = str(helpers_dir)

        try:
            helper_paths = eng.genpath(helper_root, nargout=1)
        except Exception as e:
            logger.error(f"genpath failed, falling back to root only: {e}")
            helper_paths = helper_root

        try:
            eng.addpath(helper_paths, "-end", nargout=0)
        except Exception as e:
            raise ToolError(f"addpath failed: {e}") from e

        try:
            eng.rehash(nargout=0)
        except Exception as e:
            logger.warning(f"rehash failed: {e}")

        return eng

    def close(self) -> None:
        """
        Explicitly release all extracted resources.
        Call this when the MATLAB engine is no longer needed.
        """
        self._resource_stack.close()
        self._helpers_dir = None

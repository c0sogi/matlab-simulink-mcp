import asyncio
from difflib import SequenceMatcher
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from matlab_simulink_mcp.constants import SIMLIB_DB
from matlab_simulink_mcp.engine import MatlabEngine
from matlab_simulink_mcp.security import check_path
from matlab_simulink_mcp.types import SystemDescription
from matlab_simulink_mcp.utils.clean_outputs import read_and_remove_image
from matlab_simulink_mcp.utils.logging import log_error


def register(mcp: FastMCP) -> None:
    # TODO: figure out how to undo stuff in simulink
    # TODO: maybe add system prompt as a server resource
    # TODO: Later implement a canvas based editor

    @mcp.tool
    @log_error
    async def read_simulink_system(  # pyright: ignore[reportUnusedFunction]
        path: str, detail: bool = False, open: bool = False
    ) -> Image | SystemDescription:
        """
        View a Simulink system/subsystem as either a PNG image or a detailed dictionary (if detail=True).
        Optionally open the object in MATLAB desktop.
        Detail only recommended when exact port tags or other details are needed, as it can be verbose.
        """

        eng = MatlabEngine().engine
        check_path(path)

        parent, _, rest = path.partition("/")
        parent = parent.removesuffix(".slx")
        path = parent if not rest else f"{parent}/{rest}"

        if detail:
            return SystemDescription.model_validate(
                await asyncio.to_thread(
                    eng.describe_system, path, parent, open, nargout=1
                )
            )
        else:
            ss_path: str = str(
                await asyncio.to_thread(
                    eng.snapshot_system, path, parent, open, nargout=1
                )
            )
            return read_and_remove_image(Path(ss_path))

    @mcp.tool
    @log_error
    async def search_library(query: str) -> list[str]:  # pyright: ignore[reportUnusedFunction]
        """
        Search the Simulink block library for a block name and return matching source paths.
        """

        simlib = SIMLIB_DB
        candidates = [
            (name, path) for name, entry in simlib.items() for path in entry["paths"]
        ]
        ranked = sorted(
            candidates,
            key=lambda item: SequenceMatcher(
                None, query.lower(), item[0].lower()
            ).ratio(),
            reverse=True,
        )
        return [path for _, path in ranked[:3]]

    # TODO remember the newline thing for \n
    # ['VehicleWithFourSpeedTransmission/Inertia', newline, 'Impeller']

import asyncio
from difflib import SequenceMatcher
from pathlib import Path, PurePosixPath
from typing import Any

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
        Read a Simulink model/subsystem.

        This tool supports two modes:
        - `detail=False` (default): returns a PNG snapshot (fast, best for visual inspection).
        - `detail=True`: returns a structured JSON-compatible object (best for exact port/connection reasoning).

        **Path formats (use `/` as separator):**
        - Model name: `myModel`
        - Subsystem: `myModel/SubsystemA`
        - Relative SLX file: `myModel.slx`
        - SLX in folder: `folder/myModel.slx`
        - Subsystem inside SLX: `folder/myModel.slx/SubsystemA`

        **Returns**
        - `detail=False`: `Image` (PNG)
        - `detail=True`: `SystemDescription` with:
          - `Elements`: list of blocks (Name/Type/Source + optional port arrays)
          - `Connections`: list of `{From, To}` endpoints

        **Tips**
        - Use `detail=True` only when needed; it can be verbose.
        - If you modify a model via `run_matlab_code`, call `Simulink.BlockDiagram.arrangeSystem(mdl);`
          then call this tool again to confirm.
        """

        eng = MatlabEngine().engine
        check_path(path)

        # Normalize incoming path to:
        # - main_system: argument to load_system() (can be a .slx relative file path)
        # - system_path: Simulink system/subsystem path (always uses model *name*, not file path)
        raw = path
        lower = raw.lower()
        # Use rfind so folder names containing ".slx" don't confuse parsing.
        slx_idx = lower.rfind(".slx")
        if slx_idx != -1:
            file_part = raw[: slx_idx + 4]  # includes ".slx"
            rest = raw[slx_idx + 4 :].lstrip("/")

            # Simulink system paths use just the model name (stem), not directories.
            model_name = PurePosixPath(file_part).stem
            system_path = model_name if not rest else f"{model_name}/{rest}"

            main_system = file_part
        else:
            model_name, _, rest = raw.partition("/")
            system_path = model_name if not rest else f"{model_name}/{rest}"
            main_system = model_name

        if detail:
            raw: Any = await asyncio.to_thread(eng.mcp_describe_system, system_path, main_system, open, nargout=1)

            # Helpers may return a MATLAB struct (dict-like) or a JSON string.
            if isinstance(raw, str):
                return SystemDescription.model_validate_json(raw)
            return SystemDescription.model_validate(raw)
        else:
            ss_path: str = str(
                await asyncio.to_thread(eng.mcp_snapshot_system, system_path, main_system, open, nargout=1)
            )
            return read_and_remove_image(Path(ss_path))

    @mcp.tool
    @log_error
    async def search_library(query: str) -> list[str]:  # pyright: ignore[reportUnusedFunction]
        """
        Search the Simulink block library by name and return up to 3 likely block source paths.

        Use this when you need a correct `add_block` source string, e.g.:
        - `add_block('built-in/Gain', [mdl '/G'])`
        - `add_block('simulink/Sources/Constant', [mdl '/C'])`
        """

        simlib = SIMLIB_DB
        candidates = [(name, path) for name, entry in simlib.items() for path in entry["paths"]]
        ranked = sorted(
            candidates,
            key=lambda item: SequenceMatcher(None, query.lower(), item[0].lower()).ratio(),
            reverse=True,
        )
        return [path for _, path in ranked[:3]]

    # TODO remember the newline thing for \n
    # ['VehicleWithFourSpeedTransmission/Inertia', newline, 'Impeller']

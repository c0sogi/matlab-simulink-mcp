import asyncio
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from matlab_simulink_mcp.constants import BLACKLIST_COMMANDS
from matlab_simulink_mcp.engine import MatlabEngine
from matlab_simulink_mcp.security import check_code, check_path
from matlab_simulink_mcp.utils.clean_outputs import clean_evalc, read_and_remove_image
from matlab_simulink_mcp.utils.logging import log_error


def register(mcp: FastMCP) -> None:
    @mcp.tool
    @log_error
    async def read_matlab_code(path: str, open: bool = False) -> str:  # pyright: ignore[reportUnusedFunction]
        """
        Read the contents of a MATLAB script (`.m`) or text file.

        **Input**
        - `path`: relative path only (no absolute paths, no `..`)
        - `open`: if True, open the file in MATLAB Desktop editor (best-effort)

        **Returns**
        - File contents as a string.
        """

        eng = MatlabEngine().engine
        check_path(path)

        if open:
            await asyncio.to_thread(eng.edit, path, nargout=0)
        return str(await asyncio.to_thread(eng.fileread, path, nargout=1))

    @mcp.tool
    @log_error
    async def save_matlab_code(code: str, path: str, overwrite: bool = False) -> str:  # pyright: ignore[reportUnusedFunction]
        """
        Validate and save MATLAB code to a `.m` file (sandboxed).

        This tool enforces safety rules (forbidden commands/paths) and runs a MATLAB validation helper.

        **Input**
        - `code`: MATLAB code to write
        - `path`: relative path only (no absolute paths, no `..`)
        - `overwrite`: if False, fails when the file exists

        **Returns**
        - Success message, or a message containing validation errors.
        """

        eng = MatlabEngine().engine
        check_path(path)
        check_code(code, BLACKLIST_COMMANDS)

        mode = "w" if overwrite else "x"

        cwd = await asyncio.to_thread(eng.pwd, nargout=1)
        abs_path = Path(str(cwd)) / path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        with abs_path.open(mode) as f:
            f.write(code)

        issues: list[str] = list(
            map(
                str,
                await asyncio.to_thread(eng.mcp_validate_code, path, nargout=1),  # pyright: ignore[reportArgumentType]
            )
        )
        if issues:
            return "Code saved but failed validation with errors:\n" + "\n".join(issues)
        else:
            return "Code saved and validated successfully."

    @mcp.tool
    @log_error
    async def run_matlab_code(  # pyright: ignore[reportUnusedFunction]
        code: str, get_images: bool = False
    ) -> tuple[str, *tuple[Image, ...]]:
        """
        Execute MATLAB code (sandboxed) and return MATLAB command-window output.

        Use this tool when you need MATLAB/Simulink actions not covered by a dedicated tool
        (e.g. building models, changing parameters, running simulations).

        **Safety**
        - Forbidden commands are rejected (e.g. `addpath`, `rehash`, `system`, `dos`, `unix`, `cd`, `which`, etc.).
        - Absolute paths and `..` paths inside string literals are rejected.

        **Images**
        - If `get_images=True`, the server will collect figures created during execution and return them as images.

        **Return**
        - First item: cleaned command-window text output
        - Then 0+ images (when `get_images=True`)

        **Example**
        - Create and inspect a model:
          - `new_system('m'); add_block('built-in/Gain','m/G'); save_system('m');`
          - then call `read_simulink_system('m', detail=False)`
        """

        eng = MatlabEngine().engine
        check_code(code, BLACKLIST_COMMANDS)

        imgs: list[Image] = []

        if get_images:
            await asyncio.to_thread(eng.close, "all", nargout=0)

        # Execute directly via evalc to avoid:
        # - creating any .m files in `pwd` (shadowing risk)
        # - `run(fullpath)` changing MATLAB's current folder (breaks relative paths across calls)
        text = clean_evalc(str(await asyncio.to_thread(eng.evalc, code, nargout=1)))

        await asyncio.to_thread(eng.mcp_format_system, nargout=0)

        if get_images:
            img_paths: list[str] = list(
                map(
                    str,
                    await asyncio.to_thread(eng.mcp_get_images, nargout=1),  # pyright: ignore[reportArgumentType]
                )
            )
            imgs = [read_and_remove_image(Path(p)) for p in img_paths]

        return (text, *imgs)

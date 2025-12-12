import asyncio
import tempfile
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
        Read the contents of a MATLAB script (.m) or text file.
        Optionally open the file in MATLAB desktop.
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
        Validate and save MATLAB code to a .m file.
        Optionally overwrite if the file already exists.
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
        Execute MATLAB code and return command window output as a string and images (if asked).
        Interact programatically with Simulink if the action is not covered by a tool.
        """

        eng = MatlabEngine().engine
        check_code(code, BLACKLIST_COMMANDS)

        imgs: list[Image] = []

        if get_images:
            await asyncio.to_thread(eng.close, "all", nargout=0)

        try:
            cwd = await asyncio.to_thread(eng.pwd, nargout=1)
            abs_path = Path(str(cwd)) / "canvas.m"
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            with abs_path.open("w") as f:
                f.write(code)
            pretext = None
        except PermissionError:
            with tempfile.NamedTemporaryFile("w", suffix=".m", delete=False) as f:
                f.write(code)
                abs_path = Path(f.name)
            pretext = "Could not run from current working directory. Running from temporary directory:\n"

        text = clean_evalc(str(await asyncio.to_thread(eng.evalc, f"run('{str(abs_path)}')", nargout=1)))
        if pretext:
            text = pretext + text

        abs_path.unlink(missing_ok=True)

        await asyncio.to_thread(eng.mcp_format_system, nargout=0)

        img_paths: list[str] = list(
            map(
                str,
                await asyncio.to_thread(eng.mcp_get_images, nargout=1),  # pyright: ignore[reportArgumentType]
            )
        )
        imgs = [read_and_remove_image(Path(p)) for p in img_paths]

        return (text, *imgs)

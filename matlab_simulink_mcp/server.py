import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastmcp import FastMCP

from matlab_simulink_mcp.engine import MatlabEngine

console = False

MCP_INSTRUCTION = """
1) MATLAB/Simulink access
 - Always use the MCP tools from `matlab_simulink_mcp` for any MATLAB or Simulink inspection, edits, or execution. Do not shell out to MATLAB directly.
 - Try to inspect SLX file with `read_simulink_system` to confirm you have the correct model and know the top-level blocks/parameters.
 - After creating or modifying an `.slx`, call `Simulink.BlockDiagram.arrangeSystem(model);` to auto-layout blocks.
 - After layout, call `read_simulink_system` again to visually verify the correct system and layout.
 - Every `.slx` must be self-testable: it should run immediately without extra manual setup.

2) Simulink model selection
 - Explicitly confirm the target model name/path before edits; avoid changing other models unless the user clearly requests it.
 - If multiple models exist, use `read_simulink_system` to identify top-level block names/params and choose the one matching the request.
 - Keep the scope narrow: only modify the requested model and related artifacts.
""".strip()


# Run server
def run(console: bool = False):
    # Create lifespan function
    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncGenerator[MatlabEngine, None]:
        # # do not remove server argument as it will break stuff
        """Launch pre-reqs for the server as context accessible during its run"""
        eng = MatlabEngine()
        time.sleep(1)
        eng.log_console.open()

        if not console:
            time.sleep(1)
            eng.log_console.close()

        yield eng

    try:
        from matlab_simulink_mcp.tools import matlab_code, simulink

        mcp = FastMCP(
            name="MATLAB_Simulink_MCP",
            lifespan=lifespan,
            instructions=MCP_INSTRUCTION,
        )

        matlab_code.register(mcp)
        simulink.register(mcp)

        mcp.run(transport="stdio", show_banner=False)
    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    run()

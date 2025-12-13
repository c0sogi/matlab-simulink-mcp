import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastmcp import FastMCP

from matlab_simulink_mcp.engine import MatlabEngine
from matlab_simulink_mcp.tools import matlab_code, simulink
from matlab_simulink_mcp import get_package_name

console = False

MCP_INSTRUCTION = """
You are controlling MATLAB/Simulink through MCP tools. Prefer calling tools over "explaining".

## Tool selection (high-level)
- Use `read_simulink_system` to *inspect* a model/subsystem (either image or structured JSON).
- Use `search_library` to find a library block path when you need to `add_block` in MATLAB code.
- Use `run_matlab_code` for actions not covered by a dedicated tool (build/edit models, simulate, query params).
- Use `read_matlab_code` / `save_matlab_code` for editing `.m` files (validated + sandboxed).

## `read_simulink_system` (most important)
- **Input `path` formats** (always use forward slashes `/`):
  - Model name: `myModel`
  - Subsystem: `myModel/SubsystemA`
  - Relative SLX file: `myModel.slx`
  - SLX in a folder: `folder/myModel.slx`
  - Subsystem inside SLX file: `folder/myModel.slx/SubsystemA`
- **`detail=False` (default)**: returns a PNG snapshot (best for quick visual debugging).
- **`detail=True`**: returns a JSON structure (`Elements`, `Connections`) for programmatic reasoning.
  - Use it only when you need exact port tags, block types, or connection endpoints.

## `run_matlab_code` safety + best practices
- The server blocks dangerous commands (e.g. `addpath`, `rehash`, `system`, `dos`, `unix`, `cd`, `which`, etc.).
- Avoid absolute paths and `..` paths; keep files relative to MATLAB's current working directory.
- After editing a model layout, run:
  - `Simulink.BlockDiagram.arrangeSystem(mdl);`
  - then call `read_simulink_system(mdl, detail=False)` to verify visually.

## Simulink workflow
- First confirm the exact target model name/path.
- Keep changes scoped to the requested model only.
- Prefer small incremental steps: inspect → change → inspect again.

""".strip()


# Run server
def run(console: bool = False):
    # Create lifespan function
    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncGenerator[MatlabEngine, None]:
        # # do not remove server argument as it will break stuff
        """Launch pre-reqs for the server as context accessible during its run"""
        yield MatlabEngine()

    try:
        mcp = FastMCP(
            name=get_package_name(),
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

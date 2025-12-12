import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastmcp import FastMCP

from matlab_simulink_mcp.engine import MatlabEngine

console = False


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

        mcp = FastMCP(name="MATLAB_Simulink_MCP", lifespan=lifespan)

        matlab_code.register(mcp)
        simulink.register(mcp)

        mcp.run(transport="stdio", show_banner=False)
    except Exception as e:
        print(e)
        sys.exit(1)

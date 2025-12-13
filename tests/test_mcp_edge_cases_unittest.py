from __future__ import annotations

# The upstream `mcp` client library may not ship complete type stubs in all environments.
# In this repo we run Pyright in strict mode, so we locally relax "Unknown" reports for this
# integration test while still keeping our own code fully type-annotated.
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import json
import shutil
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass(frozen=True)
class _Case:
    name: str
    setup_matlab: str
    calls: list[dict[str, Any]]


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return repr(obj)


def _ts_id() -> str:
    # Compact unique-ish suffix for model names / directories.
    return str(int(time.time() * 1000))


def _extract_text_content(resp: Any) -> str:
    if hasattr(resp, "structuredContent") and resp.structuredContent is not None:
        return _pretty(resp.structuredContent)
    if hasattr(resp, "content") and resp.content:
        first = resp.content[0]
        if hasattr(first, "text"):
            return str(first.text)
    return repr(resp)


def _structured(resp: Any) -> Any | None:
    return getattr(resp, "structuredContent", None)


def _validate_system_description(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected dict system payload, got: {type(payload)}")
    if "Elements" not in payload or "Connections" not in payload:
        raise AssertionError("Missing Elements/Connections keys")
    if not isinstance(payload["Elements"], list):
        raise AssertionError(f"Elements must be list, got: {type(payload['Elements'])}")
    if not isinstance(payload["Connections"], list):
        raise AssertionError(f"Connections must be list, got: {type(payload['Connections'])}")

    for el in payload["Elements"][:10]:
        if not isinstance(el, dict):
            raise AssertionError(f"Element must be dict, got: {type(el)}")
        if not isinstance(el.get("Name"), str):
            raise AssertionError(f"Element.Name must be str, got: {type(el.get('Name'))}")
        if not isinstance(el.get("Type"), str):
            raise AssertionError(f"Element.Type must be str, got: {type(el.get('Type'))}")

        for k in ("Inports", "Outports", "SimscapePorts"):
            v = el.get(k, None)
            if v is None:
                continue
            if not isinstance(v, list):
                raise AssertionError(f"{k} must be list|null, got: {type(v)} (value={v})")
            for p in v[:10]:
                if not isinstance(p, dict):
                    raise AssertionError(f"Port must be dict, got: {type(p)}")
                if not isinstance(p.get("name"), str):
                    raise AssertionError(f"Port.name must be str, got: {type(p.get('name'))}")
                if not isinstance(p.get("index"), int):
                    raise AssertionError(f"Port.index must be int, got: {type(p.get('index'))}")
                t = p.get("type", None)
                if t is not None and not isinstance(t, str):
                    raise AssertionError(f"Port.type must be str|null, got: {type(t)}")

    for c in payload["Connections"][:50]:
        if not isinstance(c, dict):
            raise AssertionError(f"Connection must be dict, got: {type(c)}")
        if not isinstance(c.get("From"), str):
            raise AssertionError(f"Connection.From must be str, got: {type(c.get('From'))}")
        if not isinstance(c.get("To"), str):
            raise AssertionError(f"Connection.To must be str, got: {type(c.get('To'))}")


class TestSimulinkMcpEdgeCases(unittest.IsolatedAsyncioTestCase):
    async def test_read_simulink_system_edge_cases(self) -> None:
        # Start the MCP server from this repo over stdio (via uv) and call tools through the MCP client.
        server_params = StdioServerParameters(command="uv", args=["run", "matlab-simulink-mcp"])

        sid = _ts_id()

        # IMPORTANT: absolute paths in MATLAB code are blocked by server safety checks,
        # so keep all generated artifacts under a relative test directory.
        tmp_rel = Path("tests") / "_tmp_mcp" / f"run_{sid}"
        tmp_rel_posix = tmp_rel.as_posix()

        # MATLAB setup: isolate Simulink cache/codegen under our tmp directory to avoid repo pollution.
        matlab_prelude = rf"""
try, bdclose('all'); catch, end
tmp = '{tmp_rel_posix}';
if exist(tmp, 'dir') ~= 7, mkdir(tmp); end
try
  Simulink.fileGenControl('set', 'CacheFolder', [tmp '/slcache'], 'CodeGenFolder', [tmp '/slprj']);
catch
end
"""

        # Define test cases
        mdl_empty = f"mcp_ut_empty_{sid}"
        mdl_single = f"mcp_ut_single_{sid}"
        mdl_conn = f"mcp_ut_conn_{sid}"
        mdl_ss = f"mcp_ut_ss_{sid}"
        mdl_newline = f"mcp_ut_newline_{sid}"
        mdl_slx = f"mcp_ut_slx_{sid}"
        mdl_folder = f"mcp_ut_folder_{sid}"

        file_slx = f"{tmp_rel_posix}/{mdl_slx}.slx"
        # Folder name contains ".slx" to ensure our parsing uses the LAST ".slx" in the path.
        folder = f"{tmp_rel_posix}/folder.with.slx.in.name"
        file_folder_slx = f"{folder}/{mdl_folder}.slx"

        cases: list[_Case] = [
            _Case(
                name="empty_model_detail_true_and_false",
                setup_matlab=matlab_prelude
                + rf"""
mdl = '{mdl_empty}';
try, close_system(mdl, 0); catch, end
new_system(mdl);
""",
                calls=[
                    {"tool": "read_simulink_system", "args": {"path": mdl_empty, "detail": True, "open": False}},
                    {"tool": "read_simulink_system", "args": {"path": mdl_empty, "detail": False, "open": False}},
                ],
            ),
            _Case(
                name="single_block_ports_are_arrays",
                setup_matlab=matlab_prelude
                + rf"""
mdl = '{mdl_single}';
try, close_system(mdl, 0); catch, end
new_system(mdl);
add_block('built-in/Gain', [mdl '/G']);
""",
                calls=[
                    {"tool": "read_simulink_system", "args": {"path": mdl_single, "detail": True, "open": False}},
                ],
            ),
            _Case(
                name="connections_are_emitted",
                setup_matlab=matlab_prelude
                + rf"""
mdl = '{mdl_conn}';
try, close_system(mdl, 0); catch, end
new_system(mdl);
add_block('built-in/Constant', [mdl '/C']);
add_block('built-in/Gain', [mdl '/G']);
add_block('built-in/Outport', [mdl '/Out1']);
add_line(mdl, 'C/1', 'G/1', 'autorouting', 'on');
add_line(mdl, 'G/1', 'Out1/1', 'autorouting', 'on');
""",
                calls=[
                    {"tool": "read_simulink_system", "args": {"path": mdl_conn, "detail": True, "open": False}},
                ],
            ),
            _Case(
                name="subsystem_path_with_children",
                setup_matlab=matlab_prelude
                + rf"""
mdl = '{mdl_ss}';
try, close_system(mdl, 0); catch, end
new_system(mdl);
add_block('built-in/SubSystem', [mdl '/SS']);
add_block('built-in/Gain', [mdl '/SS/G2']);
""",
                calls=[
                    {"tool": "read_simulink_system", "args": {"path": f"{mdl_ss}/SS", "detail": True, "open": False}},
                ],
            ),
            _Case(
                name="newline_in_block_name",
                setup_matlab=matlab_prelude
                + rf"""
mdl = '{mdl_newline}';
try, close_system(mdl, 0); catch, end
new_system(mdl);
add_block('built-in/Gain', [mdl '/G']);
set_param([mdl '/G'], 'Name', sprintf('A\\nB'));
""",
                calls=[
                    {"tool": "read_simulink_system", "args": {"path": mdl_newline, "detail": True, "open": False}},
                ],
            ),
            _Case(
                name="dot_slx_suffix_input",
                setup_matlab=matlab_prelude
                + rf"""
mdl = '{mdl_slx}';
try, close_system(mdl, 0); catch, end
new_system(mdl);
add_block('built-in/Gain', [mdl '/G']);
save_system(mdl, '{file_slx}');
close_system(mdl, 0);
""",
                calls=[
                    {"tool": "read_simulink_system", "args": {"path": file_slx, "detail": True, "open": False}},
                ],
            ),
            _Case(
                name="folder_slx_path_input_and_subsystem",
                setup_matlab=matlab_prelude
                + rf"""
if exist('{folder}', 'dir') ~= 7, mkdir('{folder}'); end
mdl = '{mdl_folder}';
try, close_system(mdl, 0); catch, end
new_system(mdl);
add_block('built-in/SubSystem', [mdl '/SS']);
add_block('built-in/Gain', [mdl '/SS/G2']);
save_system(mdl, '{file_folder_slx}');
close_system(mdl, 0);
""",
                calls=[
                    {"tool": "read_simulink_system", "args": {"path": file_folder_slx, "detail": True, "open": False}},
                    {
                        "tool": "read_simulink_system",
                        "args": {"path": f"{file_folder_slx}/SS", "detail": True, "open": False},
                    },
                ],
            ),
        ]

        failures: list[str] = []

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    try:
                        # Sanity: ensure MATLAB resolves our helper (no 'which' usage)
                        sanity = await session.call_tool(
                            "run_matlab_code",
                            {
                                "code": matlab_prelude
                                + r"""
s = functions(@mcp_describe_system);
disp('mcp_describe_system resolved to:');
disp(s.file);
""",
                                "get_images": False,
                            },
                        )
                        sanity_txt = _extract_text_content(sanity)
                        self.assertIn("mcp_describe_system resolved to:", sanity_txt)

                        for case in cases:
                            setup = await session.call_tool(
                                "run_matlab_code",
                                {"code": case.setup_matlab, "get_images": False},
                            )
                            if getattr(setup, "isError", False):
                                failures.append(f"{case.name}: setup error: {_extract_text_content(setup)}")
                                continue

                            for call in case.calls:
                                tool = str(call["tool"])
                                args = dict(call["args"])
                                resp = await session.call_tool(tool, args)
                                if getattr(resp, "isError", False):
                                    failures.append(f"{case.name}: {tool} error: {_extract_text_content(resp)}")
                                    continue

                                if tool == "read_simulink_system" and args.get("detail") is True:
                                    payload = _structured(resp)
                                    if payload is None:
                                        txt = _extract_text_content(resp)
                                        try:
                                            payload = json.loads(txt)
                                        except Exception as e:
                                            failures.append(f"{case.name}: cannot parse JSON: {e}; text={txt[:2000]}")
                                            continue
                                    try:
                                        _validate_system_description(payload)
                                    except Exception as e:
                                        failures.append(
                                            f"{case.name}: schema validation failed: {e}; payload={_pretty(payload)[:2000]}"
                                        )
                                else:
                                    txt = _extract_text_content(resp)
                                    if not txt:
                                        failures.append(f"{case.name}: {tool} empty response")

                    finally:
                        # Best-effort cleanup inside MATLAB (no delete/cd/addpath/etc)
                        try:
                            await session.call_tool(
                                "run_matlab_code",
                                {
                                    "code": matlab_prelude
                                    + r"""
try, bdclose('all'); catch, end
try, Simulink.fileGenControl('reset'); catch, end
""",
                                    "get_images": False,
                                },
                            )
                        except Exception:
                            # Ignore cleanup failures; we also clean from Python below.
                            pass
        finally:
            # Filesystem cleanup (outside MATLAB blacklist)
            shutil.rmtree(tmp_rel, ignore_errors=True)
            # Also remove parent _tmp_mcp if it became empty
            try:
                parent = tmp_rel.parent
                if parent.exists() and parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
            except Exception:
                pass

        if failures:
            self.fail("Edge-case failures:\n- " + "\n- ".join(failures))


if __name__ == "__main__":
    unittest.main()

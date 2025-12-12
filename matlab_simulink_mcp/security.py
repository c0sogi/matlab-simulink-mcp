import re
from pathlib import Path
from fastmcp.exceptions import ToolError


def strip_matlab_comments(code: str) -> str:
    """Removes comments from MATLAB code which could then be checked."""
    lines: list[str] = []
    for line in code.splitlines():
        line = line.split("%", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def tokenize(code: str) -> list[str]:
    """Tokenizes MATLAB code into commands and identifiers."""
    return re.findall(r"[A-Za-z_]\w*|[^\s]", code)


def check_for_commands(code: str, blacklist: set[str]):
    """Checks code for forbidden commands and raises error if found."""
    clean_code = strip_matlab_comments(code)
    tokens = tokenize(clean_code)

    for token in tokens:
        if token in blacklist:
            return f"Use of '{token}' command is not allowed."
    return None


def check_for_paths(code: str):
    """Checks string literals in code for forbidden path usage and raises error if found."""

    literals = re.findall(r"(?:'[^']*'|\"[^\"]*\")", code)

    for literal in literals:
        path_str = literal[1:-1]
        if not path_str:
            continue

        path = Path(path_str)

        if path.is_absolute():
            return "Absolute paths are not allowed. Only files on MATLAB path are accessible."
        if ".." in path.parts:
            return "Paths with .. are not allowed. Only files on MATLAB path are accessible."
        if "*" in path_str or "?" in path_str:
            return "Paths with * or ? are not allowed."


def check_code(code: str, blacklist: set[str]):
    """Checks a given code for forbidden commands or paths and raises error if any found."""
    issues = check_for_commands(code, blacklist) or check_for_paths(code)
    if issues:
        raise ToolError(issues)


def check_path(file: str):
    """Checks a given file path for absolute or parent paths and raises error if found."""
    f = Path(file)
    if f.is_absolute() or ".." in f.parts:
        raise ToolError("Access to absolute or parent paths is forbidden. Only files on MATLAB path are usable.")

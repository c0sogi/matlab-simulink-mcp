from pathlib import Path
from fastmcp.utilities.types import Image


def clean_evalc(s: str) -> str:
    return "\n".join(line.strip() for line in s.splitlines() if line.strip())


def read_and_remove_image(path: Path) -> Image:
    data: bytes = path.read_bytes()
    path.unlink(missing_ok=True)
    return Image(data=data, format="png")

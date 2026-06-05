"""Lightweight RTL parser — just enough to extract module name and signal list.

Not a real parser. Real RTL parsing requires tools like Verible or slang.
For this prototype, we only need module name and a sanity-check that the
input looks like SystemVerilog.
"""

import re
from pathlib import Path


def read_rtl(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"RTL file not found: {path}")
    content = path.read_text(encoding="utf-8")
    if not _looks_like_sv(content):
        raise ValueError(
            f"{path} does not look like SystemVerilog. "
            f"Expected to find 'module ... endmodule'."
        )
    return content


def extract_module_name(rtl: str) -> str:
    match = re.search(r"\bmodule\s+(\w+)", rtl)
    if not match:
        raise ValueError("Could not extract module name from RTL.")
    return match.group(1)


def _looks_like_sv(content: str) -> bool:
    return bool(re.search(r"\bmodule\b", content) and re.search(r"\bendmodule\b", content))
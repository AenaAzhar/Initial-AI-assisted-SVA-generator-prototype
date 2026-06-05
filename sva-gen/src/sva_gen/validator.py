"""Syntactic validation of generated SVA using Verilator.

Verilator's SystemVerilog Assertions support is a strict subset of IEEE 1800
SVA. It is sufficient for catching gross syntax errors but does not accept
constructs (e.g. `!` inside sequence expressions) that QuestaSim and
JasperGold handle fine. This validator is therefore a coarse syntax check,
not a true SVA conformance check.

We inject the assertions directly into the original module (just before
endmodule) so the assertions see all module-internal signals.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


class ValidationResult:
    def __init__(self, ok: bool, message: str):
        self.ok = ok
        self.message = message

    def __bool__(self) -> bool:
        return self.ok


def verilator_available() -> bool:
    return shutil.which("verilator") is not None


def validate_sva_syntax(rtl_module: str, assertions_sv: str) -> ValidationResult:
    if not verilator_available():
        return ValidationResult(
            ok=True,
            message="Verilator not installed; skipping syntax check. "
            "Install verilator to enable validation.",
        )

    combined = _inject_assertions_into_module(rtl_module, assertions_sv)
    if combined is None:
        return ValidationResult(
            ok=False,
            message="Could not locate `endmodule` in source to inject assertions.",
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out = tmp_path / "combined.sv"
        out.write_text(combined, encoding="utf-8")

        # Suppressed warnings are about the RTL (width mismatches, etc), not
        # about the assertions. The assertions are what we're actually testing.
        verilator_cmd = [
            "verilator",
            "--lint-only",
            "-sv",
            "-Wno-MULTITOP",
            "-Wno-WIDTHEXPAND",
            "-Wno-WIDTHTRUNC",
            "-Wno-UNUSEDSIGNAL",
            "-Wno-UNUSEDPARAM",
            "-Wno-IMPLICITSTATIC",
            str(out),
        ]

        try:
            result = subprocess.run(
                verilator_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(ok=False, message="Verilator timed out (>30s)")

        if result.returncode == 0:
            return ValidationResult(ok=True, message="Syntax check passed.")

        # Distinguish real errors from leftover warnings
        stderr = result.stderr.strip()
        if "%Error" in stderr:
            return ValidationResult(
                ok=False,
                message=(
                    f"Verilator reported errors:\n{stderr}\n\n"
                    "Note: Verilator's SVA subset is restricted; some constructs "
                    "(e.g. `!` inside sequence expressions) are rejected here but "
                    "would be accepted by QuestaSim/JasperGold."
                ),
            )

        return ValidationResult(
            ok=True,
            message=f"Syntax check passed (with warnings):\n{stderr}",
        )


def _inject_assertions_into_module(rtl_module: str, assertions: str) -> str | None:
    cleaned_assertions = _strip_header_comments(assertions)
    matches = list(re.finditer(r"\bendmodule\b", rtl_module))
    if not matches:
        return None
    last = matches[-1]
    return (
        rtl_module[: last.start()]
        + "\n\n  // ---- Injected by sva-gen for syntax validation ----\n"
        + cleaned_assertions
        + "\n  // ---- End injected block ----\n\n"
        + rtl_module[last.start() :]
    )


def _strip_header_comments(assertions: str) -> str:
    lines = assertions.splitlines()
    i = 0
    while i < len(lines) and (lines[i].startswith("//") or lines[i].strip() == ""):
        i += 1
    return "\n".join(lines[i:])
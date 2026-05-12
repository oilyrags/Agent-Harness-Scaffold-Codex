from __future__ import annotations

import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .security import ensure_within_root, redact, redacted_environment

WORKSPACE_ROOT = Path("/workspace").resolve()
mcp = FastMCP("restricted-shell")


@mcp.tool()
def run_command(command: list[str], cwd: str = "/workspace", timeout_seconds: int = 600) -> dict[str, object]:
    """Run a non-interactive command inside /workspace and return redacted output."""

    working_dir = ensure_within_root(Path(cwd), WORKSPACE_ROOT)
    completed = subprocess.run(
        command,
        cwd=str(working_dir),
        env=redacted_environment(),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": redact(completed.stdout),
        "stderr": redact(completed.stderr),
    }


@mcp.tool()
def exec(command: list[str], cwd: str = "/workspace", timeout_seconds: int = 600) -> dict[str, object]:
    """Alias for run_command."""

    return run_command(command=command, cwd=cwd, timeout_seconds=timeout_seconds)


if __name__ == "__main__":
    mcp.run()

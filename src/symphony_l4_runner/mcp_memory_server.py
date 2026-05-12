from __future__ import annotations

from typing import Any

from .memory import ProjectMemory
from .memory_cli import default_db_path


try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised by live MCP startup.
    raise RuntimeError("the mcp Python package is required for the project-memory MCP server") from exc


mcp = FastMCP("symphony-project-memory")


def _memory() -> ProjectMemory:
    return ProjectMemory(default_db_path()).initialize()


@mcp.tool()
def capture(
    kind: str,
    title: str,
    body: str,
    issue_id: str | None = None,
    source: str | None = None,
    tags: list[str] | None = None,
    confidence: float = 1.0,
) -> dict[str, Any]:
    """Capture a non-secret project-memory record."""

    record_id = _memory().capture(
        kind=kind,
        title=title,
        body=body,
        issue_id=issue_id,
        source=source,
        tags=tags or [],
        confidence=confidence,
    )
    return {"id": record_id}


@mcp.tool()
def search(
    query: str,
    limit: int = 10,
    kind: str | None = None,
    issue_id: str | None = None,
) -> list[dict[str, Any]]:
    """Search project memory with issue and kind filters."""

    return _memory().search(query, limit=limit, kind=kind, issue_id=issue_id)


@mcp.tool()
def boot_context(issue_id: str | None = None, limit: int = 8) -> str:
    """Return compact issue-aware memory context for a new autonomous run."""

    return _memory().boot_context(issue_id=issue_id, limit=limit)


@mcp.tool()
def record_run(
    issue_id: str,
    event_type: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record an autonomous execution checkpoint."""

    event_id = _memory().record_run(
        issue_id=issue_id,
        event_type=event_type,
        summary=summary,
        payload=payload or {},
    )
    return {"event_id": event_id}


@mcp.tool()
def record_decision(
    title: str,
    body: str,
    issue_id: str | None = None,
    tags: list[str] | None = None,
    source: str = "decision",
) -> dict[str, Any]:
    """Record a durable project decision."""

    record_id = _memory().record_decision(
        issue_id=issue_id,
        title=title,
        body=body,
        tags=tags or [],
        source=source,
    )
    return {"id": record_id}


if __name__ == "__main__":
    mcp.run()

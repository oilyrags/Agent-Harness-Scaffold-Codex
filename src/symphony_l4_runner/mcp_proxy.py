from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .security import contains_secret, ensure_within_root, redact, redacted_environment

LOGGER = logging.getLogger(__name__)


class MCPConfigError(ValueError):
    """Raised when MCP configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class MCPServerSpec:
    name: str
    transport: str
    command: list[str] = field(default_factory=list)
    command_env: str | None = None
    capabilities: list[str] = field(default_factory=list)
    required: bool = True
    root: Path | None = None
    restrictions: dict[str, Any] = field(default_factory=dict)

    def resolved_command(self) -> list[str]:
        if self.command:
            return self.command
        if self.command_env:
            raw = os.environ.get(self.command_env, "").strip()
            if raw:
                return raw.split()
        return []


class MCPProxy:
    def __init__(self, config_path: Path, *, dry_run: bool):
        self.config_path = config_path
        self.dry_run = dry_run
        self.workspace_root = Path("/workspace")
        self.servers = self._load(config_path)

    def validate_required_servers(self) -> None:
        missing = [name for name, spec in self.servers.items() if spec.required and not spec.capabilities]
        if missing:
            raise MCPConfigError(f"MCP servers missing capabilities: {', '.join(missing)}")

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        if contains_secret(arguments):
            raise MCPConfigError(f"refusing to send likely secret material to MCP server {server_name}")
        spec = self._server(server_name)
        self._enforce_workspace_boundaries(spec, arguments)

        if self.dry_run:
            LOGGER.info("dry_run mcp call server=%s tool=%s args=%s", server_name, tool_name, redact(arguments))
            return {"dry_run": True, "server": server_name, "tool": tool_name, "content": []}

        command = spec.resolved_command()
        if not command:
            raise MCPConfigError(f"MCP server {server_name} requires command_env={spec.command_env}")

        return await _call_mcp_stdio(command, tool_name, arguments)

    def _load(self, path: Path) -> dict[str, MCPServerSpec]:
        if not path.exists():
            raise MCPConfigError(f"missing MCP config: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        security = raw.get("security", {})
        self.workspace_root = Path(str(security.get("workspace_root", "/workspace"))).resolve()
        servers = {}
        for name, item in (raw.get("servers") or {}).items():
            root = item.get("root")
            servers[name] = MCPServerSpec(
                name=name,
                transport=str(item.get("transport", "stdio")),
                command=list(item.get("command") or []),
                command_env=item.get("command_env"),
                capabilities=list(item.get("capabilities") or []),
                required=bool(item.get("required", True)),
                root=Path(str(root)).resolve() if root else None,
                restrictions=dict(item.get("restrictions") or {}),
            )
        required_names = {
            "filesystem",
            "shell",
            "browser",
            "github",
            "jira",
            "notion",
            "miro",
            "figma",
            "lovable",
            "postgres",
            "chroma",
        }
        missing_names = sorted(required_names.difference(servers))
        if missing_names:
            raise MCPConfigError(f"missing required MCP server entries: {', '.join(missing_names)}")
        return servers

    def _server(self, name: str) -> MCPServerSpec:
        try:
            return self.servers[name]
        except KeyError as exc:
            raise MCPConfigError(f"unknown MCP server: {name}") from exc

    def _enforce_workspace_boundaries(self, spec: MCPServerSpec, arguments: dict[str, Any]) -> None:
        root = spec.root or self.workspace_root
        for key, value in arguments.items():
            if key.endswith("path") or key in {"cwd", "directory", "file"}:
                path = Path(str(value))
                if not path.is_absolute():
                    path = root / path
                ensure_within_root(path, root)


async def _call_mcp_stdio(command: list[str], tool_name: str, arguments: dict[str, Any]) -> Any:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        raise MCPConfigError("the mcp Python package is required for live MCP calls") from exc

    server_params = StdioServerParameters(
        command=command[0],
        args=command[1:],
        env=redacted_environment(),
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result

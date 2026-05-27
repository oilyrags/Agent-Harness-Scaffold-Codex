from __future__ import annotations

import asyncio
import json
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

        if server_name == "jira" and tool_name == "read_issues":
            return await _read_atlassian_jira_issues(command, arguments)

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
            "memory",
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


async def _read_atlassian_jira_issues(command: list[str], arguments: dict[str, Any]) -> dict[str, Any]:
    project_key = os.environ.get("JIRA_PROJECT_KEY", "").strip()
    if not project_key:
        raise MCPConfigError("JIRA_PROJECT_KEY must be set before live Jira polling")

    cloud_id = os.environ.get("JIRA_CLOUD_ID", "").strip()
    active_states = [str(state) for state in arguments.get("active_states", [])]

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
            if not cloud_id:
                cloud_id = await _discover_atlassian_cloud_id(session)
            jql = build_jira_active_issues_jql(project_key, active_states)
            result = await session.call_tool(
                "searchJiraIssuesUsingJql",
                {
                    "cloudId": cloud_id,
                    "jql": jql,
                    "maxResults": 10,
                    "fields": ["summary", "description", "status", "issuetype", "priority", "created", "updated"],
                    "responseContentFormat": "markdown",
                },
            )
            payload = _result_json_payload(result, "searchJiraIssuesUsingJql")
            return {"issues": normalize_atlassian_jira_issues(payload)}


async def _discover_atlassian_cloud_id(session: Any) -> str:
    result = await session.call_tool("getAccessibleAtlassianResources", {})
    resources = _result_json_payload(result, "getAccessibleAtlassianResources")
    if not isinstance(resources, list) or not resources:
        raise MCPConfigError("Jira MCP returned no accessible Atlassian resources")
    cloud_id = str(resources[0].get("id") or "").strip()
    if not cloud_id:
        raise MCPConfigError("Jira MCP resource is missing cloud id")
    return cloud_id


def _result_json_payload(result: Any, tool_name: str) -> Any:
    if getattr(result, "isError", False):
        raise MCPConfigError(f"Jira MCP tool {tool_name} failed: {_result_text(result)}")
    return extract_json_payload(_result_text(result))


def _result_text(result: Any) -> str:
    parts = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(str(text))
    return "\n".join(parts)


def build_jira_active_issues_jql(project_key: str, active_states: list[str]) -> str:
    if not project_key.strip():
        raise MCPConfigError("project key is required")
    if not active_states:
        raise MCPConfigError("at least one active Jira state is required")
    escaped_project = project_key.strip().replace('"', '\\"')
    escaped_states = [state.replace('"', '\\"') for state in active_states]
    state_clause = ", ".join(f'"{state}"' for state in escaped_states)
    return f'project = "{escaped_project}" AND status in ({state_clause}) AND issuetype not in ("Epic") ORDER BY updated DESC'


def extract_json_payload(text: str) -> Any:
    stripped = text.strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char not in "{[":
            continue
        try:
            payload, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        return payload
    raise MCPConfigError("MCP result did not contain JSON")


def normalize_atlassian_jira_issues(payload: Any) -> list[dict[str, Any]]:
    raw_issues = payload.get("issues", []) if isinstance(payload, dict) else []
    issues: list[dict[str, Any]] = []
    for issue in raw_issues:
        if not isinstance(issue, dict):
            continue
        fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
        status = fields.get("status") if isinstance(fields.get("status"), dict) else {}
        item = {
            "id": str(issue.get("id") or issue.get("key") or ""),
            "identifier": str(issue.get("key") or ""),
            "title": str(fields.get("summary") or ""),
            "description": fields.get("description"),
            "status": str(status.get("name") or ""),
            "url": issue.get("self"),
        }
        if item["id"] and item["identifier"] and item["title"]:
            issues.append(item)
    return issues

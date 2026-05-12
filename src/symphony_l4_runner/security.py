from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|client[_-]?secret)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"(?i)authorization:\s*(bearer|basic)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9_=-]{24,}\.[A-Za-z0-9_=-]{6,}\.[A-Za-z0-9_=-]{20,}\b"),
)

SECRET_VALUE_ENV_HINTS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "CLIENT_SECRET", "AUTH")


class SecretWriteError(ValueError):
    """Raised when a write target would persist likely secret material."""


def redact(value: Any) -> str:
    """Return a display-safe string with likely secrets masked."""

    if not isinstance(value, str):
        try:
            value = json.dumps(value, sort_keys=True, default=str)
        except TypeError:
            value = str(value)

    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: _mask_match(match.group(0)), redacted)
    return redacted


def contains_secret(value: Any) -> bool:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def redacted_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return a conservative environment for subprocesses without credential values."""

    allowed = {
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
        "TERM",
        "CODEX_HOME",
        "PYTHONPATH",
        "PYTHONDONTWRITEBYTECODE",
        "PROJECT_MEMORY_DB",
        "PLAYWRIGHT_BROWSERS_PATH",
        "WORKSPACE_ROOT",
        "PLANS_DIR",
        "SYMPHONY_MODE",
        "SYMPHONY_DRY_RUN",
        "SYMPHONY_LOG_LEVEL",
    }
    env = {key: value for key, value in os.environ.items() if key in allowed}
    if extra:
        for key, value in extra.items():
            if any(hint in key.upper() for hint in SECRET_VALUE_ENV_HINTS):
                continue
            env[key] = value
    return env


def secure_write_text(path: Path, content: str, *, mode: int = 0o644) -> Path:
    """Atomically write text only when it does not contain likely secrets."""

    if contains_secret(content):
        raise SecretWriteError(f"refusing to write likely secret material to {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()
    return path


def ensure_within_root(path: Path, root: Path) -> Path:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"path escapes workspace root: {resolved_path}")
    return resolved_path


def _mask_match(text: str) -> str:
    if ":" in text:
        prefix = text.split(":", 1)[0]
        return f"{prefix}: [REDACTED]"
    if "=" in text:
        prefix = text.split("=", 1)[0]
        return f"{prefix}=[REDACTED]"
    return "[REDACTED]"

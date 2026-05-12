from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Issue:
    id: str
    identifier: str
    title: str
    description: str | None = None
    priority: int | None = None
    state: str = "To Do"
    branch_name: str | None = None
    url: str | None = None
    labels: list[str] = field(default_factory=list)
    blocked_by: list[dict[str, Any]] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "Issue":
        identifier = str(value.get("identifier") or value.get("key") or value.get("issue_key") or "")
        issue_id = str(value.get("id") or identifier)
        title = str(value.get("title") or value.get("summary") or "")
        if not issue_id or not identifier or not title:
            raise ValueError("issue requires id, identifier, and title")
        labels = [str(label).lower() for label in value.get("labels", [])]
        return cls(
            id=issue_id,
            identifier=identifier,
            title=title,
            description=value.get("description"),
            priority=value.get("priority"),
            state=str(value.get("state") or value.get("status") or "To Do"),
            branch_name=value.get("branch_name"),
            url=value.get("url"),
            labels=labels,
            blocked_by=list(value.get("blocked_by", [])),
            created_at=value.get("created_at"),
            updated_at=value.get("updated_at"),
        )

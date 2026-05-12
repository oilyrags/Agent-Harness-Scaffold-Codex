from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .security import SecretWriteError, contains_secret


class MemorySecretError(SecretWriteError):
    """Raised when project memory input contains likely secret material."""


class ProjectMemory:
    """SQLite-backed long-term project memory for autonomous Symphony runs."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)

    def initialize(self) -> "ProjectMemory":
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    issue_id TEXT,
                    source TEXT,
                    tags TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    secret_scan_status TEXT NOT NULL DEFAULT 'passed'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_issue ON memory_records(issue_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_kind ON memory_records(kind)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_updated ON memory_records(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_issue ON run_events(issue_id)")
            self._ensure_search_table(conn)
        return self

    def capture(
        self,
        *,
        kind: str,
        title: str,
        body: str,
        issue_id: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        confidence: float = 1.0,
    ) -> int:
        self._reject_secret_input(
            {
                "kind": kind,
                "title": title,
                "body": body,
                "issue_id": issue_id,
                "source": source,
                "tags": tags or [],
            }
        )
        self.initialize()
        with self._connect() as conn:
            return self._insert_record(
                conn,
                kind=kind,
                title=title,
                body=body,
                issue_id=issue_id,
                source=source,
                tags=tags or [],
                confidence=confidence,
            )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        kind: str | None = None,
        issue_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.initialize()
        safe_limit = max(1, min(int(limit), 50))
        tokens = _query_tokens(query)
        with self._connect() as conn:
            if not tokens:
                return self._latest(conn, limit=safe_limit, kind=kind, issue_id=issue_id)
            if self._fts_enabled(conn):
                try:
                    return self._search_fts(
                        conn,
                        tokens=tokens,
                        limit=safe_limit,
                        kind=kind,
                        issue_id=issue_id,
                    )
                except sqlite3.OperationalError:
                    return self._search_like(
                        conn,
                        tokens=tokens,
                        limit=safe_limit,
                        kind=kind,
                        issue_id=issue_id,
                    )
            return self._search_like(conn, tokens=tokens, limit=safe_limit, kind=kind, issue_id=issue_id)

    def boot_context(self, *, issue_id: str | None = None, limit: int = 8) -> str:
        self.initialize()
        safe_limit = max(1, min(int(limit), 25))
        with self._connect() as conn:
            rows = self._boot_rows(conn, issue_id=issue_id, limit=safe_limit)

        lines = ["# Project Memory Boot Context", ""]
        if not rows:
            lines.append("No project memory captured yet.")
            return "\n".join(lines) + "\n"

        for row in rows:
            item = self._row_to_dict(row)
            scope = item["issue_id"] or "global"
            tags = f" tags={','.join(item['tags'])}" if item["tags"] else ""
            body = _compact(item["body"], limit=420)
            lines.append(f"- [{item['kind']}][{scope}] {item['title']}{tags}: {body}")
        return "\n".join(lines) + "\n"

    def record_run(
        self,
        *,
        issue_id: str,
        event_type: str,
        summary: str,
        payload: dict[str, Any] | None = None,
    ) -> int:
        payload = payload or {}
        self._reject_secret_input(
            {
                "issue_id": issue_id,
                "event_type": event_type,
                "summary": summary,
                "payload": payload,
            }
        )
        self.initialize()
        with self._connect() as conn:
            now = _now()
            cursor = conn.execute(
                """
                INSERT INTO run_events (issue_id, event_type, summary, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (issue_id, event_type, summary, json.dumps(payload, sort_keys=True), now),
            )
            event_id = int(cursor.lastrowid)
            self._insert_record(
                conn,
                kind="run-summary",
                title=f"{event_type}: {issue_id}",
                body=summary,
                issue_id=issue_id,
                source=f"run-event:{event_id}",
                tags=[event_type],
                confidence=1.0,
            )
            return event_id

    def record_decision(
        self,
        *,
        issue_id: str | None,
        title: str,
        body: str,
        tags: list[str] | None = None,
        source: str = "decision",
    ) -> int:
        return self.capture(
            kind="decision",
            title=title,
            body=body,
            issue_id=issue_id,
            source=source,
            tags=tags or [],
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_search_table(self, conn: sqlite3.Connection) -> None:
        if self._meta(conn, "fts_enabled") is not None:
            if self._fts_enabled(conn):
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_records_fts
                    USING fts5(title, body, source, tags, content='')
                    """
                )
            else:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_records_fts (
                        rowid INTEGER PRIMARY KEY,
                        title TEXT NOT NULL,
                        body TEXT NOT NULL,
                        source TEXT,
                        tags TEXT NOT NULL DEFAULT '[]'
                    )
                    """
                )
            return

        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_records_fts
                USING fts5(title, body, source, tags, content='')
                """
            )
            self._set_meta(conn, "fts_enabled", "true")
        except sqlite3.OperationalError:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_records_fts (
                    rowid INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    source TEXT,
                    tags TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            self._set_meta(conn, "fts_enabled", "false")

    def _insert_record(
        self,
        conn: sqlite3.Connection,
        *,
        kind: str,
        title: str,
        body: str,
        issue_id: str | None,
        source: str | None,
        tags: list[str],
        confidence: float,
    ) -> int:
        kind = _required(kind, "kind")
        title = _required(title, "title")
        body = _required(body, "body")
        tag_json = json.dumps([str(tag) for tag in tags], sort_keys=True)
        now = _now()
        cursor = conn.execute(
            """
            INSERT INTO memory_records
                (kind, title, body, issue_id, source, tags, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kind,
                title,
                body,
                _empty_to_none(issue_id),
                _empty_to_none(source),
                tag_json,
                float(confidence),
                now,
                now,
            ),
        )
        record_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO memory_records_fts (rowid, title, body, source, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (record_id, title, body, source or "", tag_json),
        )
        return record_id

    def _search_fts(
        self,
        conn: sqlite3.Connection,
        *,
        tokens: list[str],
        limit: int,
        kind: str | None,
        issue_id: str | None,
    ) -> list[dict[str, Any]]:
        where = ["memory_records_fts MATCH ?"]
        params: list[Any] = [" ".join(tokens)]
        self._append_filters(where, params, kind=kind, issue_id=issue_id)
        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT r.*, bm25(memory_records_fts) AS score
            FROM memory_records_fts
            JOIN memory_records r ON r.id = memory_records_fts.rowid
            WHERE {' AND '.join(where)}
            ORDER BY score, r.updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _search_like(
        self,
        conn: sqlite3.Connection,
        *,
        tokens: list[str],
        limit: int,
        kind: str | None,
        issue_id: str | None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        for token in tokens:
            where.append("(title LIKE ? OR body LIKE ? OR source LIKE ? OR tags LIKE ?)")
            like = f"%{token}%"
            params.extend([like, like, like, like])
        self._append_filters(where, params, kind=kind, issue_id=issue_id)
        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT *, 0.0 AS score
            FROM memory_records
            WHERE {' AND '.join(where)}
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _latest(
        self,
        conn: sqlite3.Connection,
        *,
        limit: int,
        kind: str | None,
        issue_id: str | None,
    ) -> list[dict[str, Any]]:
        where = ["1 = 1"]
        params: list[Any] = []
        self._append_filters(where, params, kind=kind, issue_id=issue_id)
        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT *, 0.0 AS score
            FROM memory_records
            WHERE {' AND '.join(where)}
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _boot_rows(self, conn: sqlite3.Connection, *, issue_id: str | None, limit: int) -> list[sqlite3.Row]:
        if issue_id:
            return conn.execute(
                """
                SELECT *, 0.0 AS score
                FROM memory_records
                WHERE issue_id = ? OR issue_id IS NULL OR issue_id = ''
                ORDER BY CASE WHEN issue_id = ? THEN 0 ELSE 1 END, updated_at DESC
                LIMIT ?
                """,
                (issue_id, issue_id, limit),
            ).fetchall()
        return conn.execute(
            """
            SELECT *, 0.0 AS score
            FROM memory_records
            WHERE issue_id IS NULL OR issue_id = ''
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    def _append_filters(
        self,
        where: list[str],
        params: list[Any],
        *,
        kind: str | None,
        issue_id: str | None,
    ) -> None:
        if kind:
            where.append("r.kind = ?" if where and where[0].startswith("memory_records_fts") else "kind = ?")
            params.append(kind)
        if issue_id:
            where.append("r.issue_id = ?" if where and where[0].startswith("memory_records_fts") else "issue_id = ?")
            params.append(issue_id)

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        raw_tags = row["tags"] or "[]"
        try:
            tags = json.loads(raw_tags)
        except json.JSONDecodeError:
            tags = []
        return {
            "id": row["id"],
            "kind": row["kind"],
            "title": row["title"],
            "body": row["body"],
            "issue_id": row["issue_id"],
            "source": row["source"],
            "tags": tags,
            "confidence": row["confidence"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "score": row["score"] if "score" in row.keys() else 0.0,
        }

    def _meta(self, conn: sqlite3.Connection, key: str) -> str | None:
        row = conn.execute("SELECT value FROM memory_meta WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def _set_meta(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            "INSERT INTO memory_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def _fts_enabled(self, conn: sqlite3.Connection) -> bool:
        return self._meta(conn, "fts_enabled") == "true"

    def _reject_secret_input(self, value: Any) -> None:
        if contains_secret(value):
            raise MemorySecretError("refusing to store likely secret material in project memory")


def _query_tokens(query: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9_]+", query) if token]


def _required(value: str | None, name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{name} is required")
    return str(value).strip()


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _compact(value: str, *, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

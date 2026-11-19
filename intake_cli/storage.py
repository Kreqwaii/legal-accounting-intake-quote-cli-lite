"""SQLite persistence and Markdown/JSON/CSV export for client intakes."""

from contextlib import contextmanager
import csv
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .pricing import calculate_quote, get_category


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT DEFAULT '',
    category TEXT NOT NULL,
    domain TEXT NOT NULL,
    urgency TEXT NOT NULL DEFAULT 'standard',
    complexity TEXT NOT NULL DEFAULT 'medium',
    package TEXT NOT NULL DEFAULT 'one-time',
    extra_hours INTEGER NOT NULL DEFAULT 0,
    total_quote REAL NOT NULL,
    notes TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checklist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    doc_name TEXT NOT NULL,
    received INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class IntakeStorage:
    def __init__(self, db_path: str = "intake.db") -> None:
        self.db_path = str(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def create_intake(
        self,
        client_name: str,
        email: str,
        category: str,
        company: str = "",
        urgency: str = "standard",
        complexity: str = "medium",
        package: str = "one-time",
        extra_hours: int = 0,
        notes: str = "",
    ) -> Dict[str, Any]:
        self.init_db()
        spec = get_category(category)
        quote = calculate_quote(
            category_code=category,
            urgency=urgency,
            complexity=complexity,
            package=package,
            extra_hours=extra_hours,
        )
        created_at = _now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO clients (
                    client_name, email, company, category, domain,
                    urgency, complexity, package, extra_hours, total_quote,
                    notes, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
                """,
                (
                    client_name,
                    email,
                    company,
                    spec.code,
                    spec.domain,
                    urgency,
                    complexity,
                    package,
                    extra_hours,
                    quote["total_quote"],
                    notes,
                    created_at,
                ),
            )
            client_id = cur.lastrowid
            for doc in spec.documents:
                conn.execute(
                    "INSERT INTO checklist_items (client_id, doc_name, received) VALUES (?, ?, 0)",
                    (client_id, doc),
                )
        return self.get_client(client_id)  # type: ignore[return-value]

    def get_client(self, client_id: int) -> Optional[Dict[str, Any]]:
        self.init_db()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
            if row is None:
                return None
            docs = conn.execute(
                "SELECT id, doc_name, received FROM checklist_items WHERE client_id = ? ORDER BY id",
                (client_id,),
            ).fetchall()
        data = dict(row)
        data["checklist"] = [
            {"id": d["id"], "doc_name": d["doc_name"], "received": bool(d["received"])}
            for d in docs
        ]
        return data

    def list_clients(self, domain: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self.init_db()
        query = "SELECT * FROM clients WHERE 1=1"
        params: List[Any] = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def mark_document(self, client_id: int, doc_index: int, received: bool = True) -> Dict[str, Any]:
        client = self.get_client(client_id)
        if not client:
            raise ValueError(f"Client ID {client_id} not found.")
        checklist = client["checklist"]
        if doc_index < 1 or doc_index > len(checklist):
            raise ValueError(f"Document index {doc_index} out of range (1..{len(checklist)}).")
        item_id = checklist[doc_index - 1]["id"]
        with self._connect() as conn:
            conn.execute(
                "UPDATE checklist_items SET received = ? WHERE id = ?",
                (1 if received else 0, item_id),
            )
        return self.get_client(client_id)  # type: ignore[return-value]

    def update_status(self, client_id: int, status: str) -> Dict[str, Any]:
        valid = {"new", "quoted", "retained", "closed"}
        if status not in valid:
            raise ValueError(f"Invalid status '{status}'. Choose: {', '.join(sorted(valid))}")
        client = self.get_client(client_id)
        if not client:
            raise ValueError(f"Client ID {client_id} not found.")
        with self._connect() as conn:
            conn.execute("UPDATE clients SET status = ? WHERE id = ?", (status, client_id))
        return self.get_client(client_id)  # type: ignore[return-value]

    def export_client(self, client_id: int, fmt: str = "markdown") -> str:
        client = self.get_client(client_id)
        if not client:
            raise ValueError(f"Client ID {client_id} not found.")
        fmt_lower = fmt.lower()
        if fmt_lower == "json":
            return json.dumps(client, indent=2)
        if fmt_lower == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                [
                    "id",
                    "client_name",
                    "email",
                    "company",
                    "category",
                    "domain",
                    "urgency",
                    "complexity",
                    "package",
                    "extra_hours",
                    "total_quote",
                    "status",
                    "created_at",
                ]
            )
            writer.writerow(
                [
                    client["id"],
                    client["client_name"],
                    client["email"],
                    client["company"],
                    client["category"],
                    client["domain"],
                    client["urgency"],
                    client["complexity"],
                    client["package"],
                    client["extra_hours"],
                    client["total_quote"],
                    client["status"],
                    client["created_at"],
                ]
            )
            return buf.getvalue()
        if fmt_lower in ("markdown", "md"):
            lines = [
                f"# Client Intake Card #{client['id']}: {client['client_name']}",
                "",
                f"- **Email:** {client['email']}",
                f"- **Company:** {client['company'] or 'N/A'}",
                f"- **Domain:** {client['domain']}",
                f"- **Category:** {client['category']}",
                f"- **Urgency / Complexity:** {client['urgency']} / {client['complexity']}",
                f"- **Package:** {client['package']} (Extra Hours: {client['extra_hours']})",
                f"- **Estimated Retainer Quote:** ${client['total_quote']:.2f}",
                f"- **Status:** {client['status']}",
                f"- **Created At:** {client['created_at']}",
                "",
                "## Document Checklist",
            ]
            for idx, item in enumerate(client["checklist"], start=1):
                mark = "x" if item["received"] else " "
                lines.append(f"- [{mark}] {idx}. {item['doc_name']}")
            if client["notes"]:
                lines.extend(["", "## Notes", client["notes"]])
            return "\n".join(lines) + "\n"
        raise ValueError(f"Unsupported export format '{fmt}'. Choose: markdown, json, csv.")

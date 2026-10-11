from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def open_db(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA busy_timeout = 5000")
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
    _make_append_only(db)
    return db


def _make_append_only(db: sqlite3.Connection) -> None:
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )]
    for table in tables:
        for operation in ("UPDATE", "DELETE"):
            db.execute(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} "
                f"BEFORE {operation} ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
            )
    db.commit()


@dataclass(frozen=True, slots=True)
class IngestResult:
    added: int
    duplicates: int


def ingest_directory(db: sqlite3.Connection, directory: str | Path) -> IngestResult:
    added = duplicates = 0
    with db:
        for path in sorted(Path(directory).glob("*.txt")):
            content = path.read_text(encoding="utf-8-sig")
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            inserted = db.execute(
                "INSERT OR IGNORE INTO documents(sha256, content) VALUES (?, ?)", (digest, content)
            ).rowcount
            document_id = db.execute("SELECT id FROM documents WHERE sha256 = ?", (digest,)).fetchone()[0]
            db.execute(
                "INSERT OR IGNORE INTO document_sources(document_id, locator) VALUES (?, ?)",
                (document_id, path.as_posix()),
            )
            added += inserted
            duplicates += not inserted
    return IngestResult(added, duplicates)

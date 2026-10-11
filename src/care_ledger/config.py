from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    model: str
    reasoning_effort: str
    extraction_version: str


def load_settings() -> Settings:
    load_dotenv(override=False)
    return Settings(
        database_path=Path(os.getenv("CARE_LEDGER_DB", "artifacts/care_ledger.sqlite")),
        model=os.getenv("CARE_LEDGER_MODEL", "gpt-5.4-mini"),
        reasoning_effort=os.getenv("CARE_LEDGER_REASONING_EFFORT", "medium"),
        extraction_version=os.getenv("CARE_LEDGER_EXTRACTION_VERSION", "llm-v1"),
    )

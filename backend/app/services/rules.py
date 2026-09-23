"""Loads versioned nutrition & safety rules.

Priority: active row in *_rules_config DB tables → bundled JSON config file.
This lets ops change limits (e.g. AI daily limits, deficit caps) without any
Android code changes.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text

from ..db import db_conn
from ..settings import get_settings


@lru_cache
def _file_rules(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load(table: str, file_path: str) -> dict:
    try:
        with db_conn() as conn:
            row = conn.execute(
                text(f"SELECT rules FROM {table} WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 1")
            ).fetchone()
        if row:
            rules = row[0]
            return rules if isinstance(rules, dict) else json.loads(rules)
    except Exception:
        pass  # DB unavailable → fall back to bundled config
    return _file_rules(file_path)


def get_nutrition_rules() -> dict:
    return _load("nutrition_rules_config", get_settings().nutrition_rules_path)


def get_safety_rules() -> dict:
    return _load("safety_rules_config", get_settings().safety_rules_path)

# -*- coding: utf-8 -*-
"""Config helpers for the slim workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(value: str, base: Path) -> Optional[Path]:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def deep_update(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

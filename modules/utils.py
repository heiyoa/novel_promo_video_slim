# -*- coding: utf-8 -*-
"""Small shared helpers."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Optional


def safe_filename(text: str, max_len: int = 50) -> str:
    cleaned = re.sub(r"[\\\\/:*?\"<>|]", "_", text or "")
    cleaned = "_".join(cleaned.split())
    return cleaned[:max_len] or "book"


def safe_draft_name(text: str, fallback: str = "NovelPromoVideo") -> str:
    cleaned = re.sub(r"[\\\\/:*?\"<>|]", "_", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or fallback


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def pick_first_value(data: Dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        value = (data.get(key) or "").strip()
        if value:
            return value
    return ""


def build_novel_text(book: Dict[str, str], promo: Dict[str, str], priority: Iterable[str]) -> str:
    combined = dict(book or {})
    combined.update({k: v for k, v in (promo or {}).items() if v})
    return pick_first_value(combined, priority)

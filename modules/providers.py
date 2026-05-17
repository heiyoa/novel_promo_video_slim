# -*- coding: utf-8 -*-
"""Provider interfaces for books DB and local music."""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class BookRecord:
    source_key: str
    title: str
    alias: str
    platform: str
    tags: str
    synopsis: str
    chapter_content: str
    promo_code: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "source_key": self.source_key,
            "title": self.title,
            "alias": self.alias,
            "platform": self.platform,
            "tags": self.tags,
            "synopsis": self.synopsis,
            "chapter_content": self.chapter_content,
            "promo_code": self.promo_code,
        }


class BooksProvider:
    def select_books(
        self,
        limit: int,
        book_name: Optional[str],
        list_type: Optional[str],
        include_complete: bool,
        required_fields: Iterable[str],
    ) -> List[BookRecord]:
        raise NotImplementedError

    def update_promo(self, source_key: str, promo: Dict[str, str], existing_synopsis: str) -> int:
        raise NotImplementedError

    def close(self) -> None:
        return None


class SQLiteBooksProvider(BooksProvider):
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        required = {
            "synopsis": "TEXT",
            "chapter_content": "TEXT",
            "promo_code": "TEXT",
            "updated_at": "TEXT",
        }
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(books)")}
        for name, col_type in required.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE books ADD COLUMN {name} {col_type}")
        self.conn.commit()

    def select_books(
        self,
        limit: int,
        book_name: Optional[str],
        list_type: Optional[str],
        include_complete: bool,
        required_fields: Iterable[str],
    ) -> List[BookRecord]:
        filters = ["(title <> '' OR alias <> '')"]
        params: List[str] = []

        if list_type:
            filters.append("list_type = ?")
            params.append(list_type)

        if book_name:
            filters.append("(title LIKE ? OR alias LIKE ?)")
            keyword = f"%{book_name}%"
            params.extend([keyword, keyword])

        if not include_complete:
            missing_parts = []
            for field in required_fields:
                missing_parts.append(f"({field} IS NULL OR {field} = '')")
            filters.append("(" + " OR ".join(missing_parts) + ")")

        where_sql = " AND ".join(filters)
        sql = (
            "SELECT source_key, title, alias, platform, tags, synopsis, chapter_content, promo_code "
            f"FROM books WHERE {where_sql} ORDER BY updated_at DESC, row_index ASC LIMIT ?"
        )
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [
            BookRecord(
                source_key=row["source_key"],
                title=row["title"] or "",
                alias=row["alias"] or "",
                platform=row["platform"] or "",
                tags=row["tags"] or "",
                synopsis=row["synopsis"] or "",
                chapter_content=row["chapter_content"] or "",
                promo_code=row["promo_code"] or "",
            )
            for row in rows
        ]

    def update_promo(self, source_key: str, promo: Dict[str, str], existing_synopsis: str) -> int:
        fields: Dict[str, str] = {}
        plot_summary = (promo.get("plot_summary") or "").strip()
        chapter_content = (promo.get("chapter_content") or "").strip()
        promo_code = (promo.get("promo_code") or "").strip()
        current_synopsis = (existing_synopsis or "").strip()

        if plot_summary and not current_synopsis:
            fields["synopsis"] = plot_summary
        if chapter_content:
            fields["chapter_content"] = chapter_content
        if promo_code:
            fields["promo_code"] = promo_code

        if not fields:
            return 0

        fields["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        assignments = ", ".join([f"{col}=?" for col in fields])
        values = [fields[col] for col in fields]
        values.append(source_key)
        cursor = self.conn.execute(f"UPDATE books SET {assignments} WHERE source_key=?", values)
        self.conn.commit()
        return cursor.rowcount or 0

    def close(self) -> None:
        if self.conn:
            self.conn.close()


class MusicProvider:
    def pick_audio(self) -> Optional[Path]:
        raise NotImplementedError


class LocalRandomMusicProvider(MusicProvider):
    def __init__(self, music_dir: Path, extensions: Optional[Iterable[str]] = None) -> None:
        self.music_dir = music_dir
        self.extensions = [ext.lower() for ext in (extensions or [".mp3"])]

    def pick_audio(self) -> Optional[Path]:
        if not self.music_dir.exists():
            return None
        files: List[Path] = []
        for ext in self.extensions:
            files.extend(self.music_dir.glob(f"*{ext}"))
        return random.choice(files) if files else None

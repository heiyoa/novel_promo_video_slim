# -*- coding: utf-8 -*-
"""Slim promo + video workflow entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
MODULES_DIR = ROOT / "modules"
if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))

from config_utils import load_json, resolve_path, dump_json  # noqa: E402
from promo_fetcher import PromoFetcher  # noqa: E402
from providers import LocalRandomMusicProvider, SQLiteBooksProvider  # noqa: E402
from utils import contains_cjk, safe_filename  # noqa: E402
from video_pipeline import run_video_pipeline  # noqa: E402


def build_promo_candidates(title: str, alias: str) -> List[str]:
    title = (title or "").strip()
    alias = (alias or "").strip()
    if alias and contains_cjk(alias):
        candidates = [alias, title]
    else:
        candidates = [title, alias]
    result: List[str] = []
    for item in candidates:
        if item and item not in result:
            result.append(item)
    return result


def has_missing_fields(book: Dict[str, str], fields: List[str]) -> List[str]:
    missing = []
    for field in fields:
        if not (book.get(field) or "").strip():
            missing.append(field)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Slim promo + video workflow")
    parser.add_argument("--system-config", default="config/system_config.json")
    parser.add_argument("--workflow-config", default="config/workflow_config.json")
    parser.add_argument("--book-name", default="")
    parser.add_argument("--book-limit", type=int, default=0)
    parser.add_argument("--include-complete", action="store_true")
    parser.add_argument("--skip-promo", action="store_true")
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--job-output", default="")
    args = parser.parse_args()

    system_config_path = resolve_path(args.system_config, ROOT) or (ROOT / args.system_config)
    workflow_config_path = resolve_path(args.workflow_config, ROOT) or (ROOT / args.workflow_config)

    if not system_config_path.exists():
        print(f"[ERROR] system config missing: {system_config_path}")
        return
    if not workflow_config_path.exists():
        print(f"[ERROR] workflow config missing: {workflow_config_path}")
        return

    system_config = load_json(system_config_path)
    workflow_config = load_json(workflow_config_path)

    steps = workflow_config.get("steps", {}) if isinstance(workflow_config, dict) else {}
    if args.skip_promo:
        steps["fetch_promo"] = False
    if args.skip_video:
        steps["run_video"] = False

    selection = workflow_config.get("book_selection", {}) if isinstance(workflow_config, dict) else {}
    if args.book_name:
        selection["book_name"] = args.book_name
    if args.book_limit:
        selection["book_limit"] = args.book_limit
    if args.include_complete:
        selection["include_complete"] = True

    required_fields = workflow_config.get("promo_required_fields", []) or []

    paths_config = system_config.get("paths", {}) if isinstance(system_config, dict) else {}
    providers_config = system_config.get("providers", {}) if isinstance(system_config, dict) else {}

    books_config = providers_config.get("books", {}) if isinstance(providers_config, dict) else {}
    if books_config.get("type") != "sqlite":
        print("[ERROR] Only sqlite books provider is supported.")
        return
    db_path_value = (
        books_config.get("sqlite", {}).get("path")
        if isinstance(books_config.get("sqlite", {}), dict)
        else None
    ) or paths_config.get("db_path", "data/books.db")
    db_path = resolve_path(str(db_path_value), ROOT) or (ROOT / "data" / "books.db")
    books_provider = SQLiteBooksProvider(db_path)

    music_config = providers_config.get("music", {}) if isinstance(providers_config, dict) else {}
    if music_config.get("type") != "local_random":
        print("[ERROR] Only local_random music provider is supported.")
        books_provider.close()
        return
    local_cfg = music_config.get("local_random", {}) if isinstance(music_config, dict) else {}
    music_dir_value = local_cfg.get("music_dir") or paths_config.get("music_audio_dir", "assets/music_audio")
    music_dir = resolve_path(str(music_dir_value), ROOT) or (ROOT / "assets" / "music_audio")
    extensions = local_cfg.get("extensions", [".mp3"])
    music_provider = LocalRandomMusicProvider(music_dir, extensions)

    list_type = str(selection.get("list_type") or "").strip().lower()
    list_type_value = None if list_type in ("", "all") else list_type
    book_name = str(selection.get("book_name") or "").strip() or None
    book_limit = int(selection.get("book_limit") or 1)
    include_complete = bool(selection.get("include_complete"))

    books = books_provider.select_books(
        limit=book_limit,
        book_name=book_name,
        list_type=list_type_value,
        include_complete=include_complete,
        required_fields=required_fields,
    )

    if not books:
        print("[ERROR] No books selected.")
        books_provider.close()
        return

    promo_fetcher = None
    if steps.get("fetch_promo", True):
        promo_fetcher = PromoFetcher(system_config.get("edge", {}), system_config.get("promo_fetch", {}))

    outputs_dir = resolve_path(str(paths_config.get("outputs_dir", "outputs")), ROOT) or (ROOT / "outputs")
    promo_outputs_dir = resolve_path(
        str(paths_config.get("promo_outputs_dir", outputs_dir / "promo")), ROOT
    ) or (outputs_dir / "promo")
    promo_outputs_dir.mkdir(parents=True, exist_ok=True)

    draft_folder_value = paths_config.get("draft_folder", "")
    draft_folder = resolve_path(str(draft_folder_value), ROOT) if draft_folder_value else None

    job_output_value = args.job_output or paths_config.get("job_output_path", "")
    job_output_path = resolve_path(str(job_output_value), ROOT) if job_output_value else None
    if job_output_path is None:
        job_output_path = outputs_dir / "job_output.json"

    job_books: List[Dict[str, object]] = []
    video_outputs: List[Dict[str, object]] = []

    for book in books:
        book_dict = book.to_dict()
        missing_fields = has_missing_fields(book_dict, required_fields)
        promo_result: Dict[str, str] = {}
        promo_error = ""
        promo_query = ""

        if promo_fetcher and missing_fields:
            candidates = build_promo_candidates(book.title, book.alias)
            for candidate in candidates:
                promo_query = candidate
                promo_result = promo_fetcher.fetch(candidate)
                if promo_result.get("error"):
                    promo_error = promo_result.get("error", "")
                    continue
                if any((promo_result.get(key) or "").strip() for key in ["plot_summary", "chapter_content", "promo_code"]):
                    break

            output_name = safe_filename(book.title or book.alias or candidate)
            promo_output_path = promo_outputs_dir / f"promo_{output_name}.json"
            promo_payload = {
                "book_title": book.title,
                "book_alias": book.alias,
                "promo_query": promo_query,
                "result": promo_result,
                "error": promo_error,
                "fetched_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            }
            promo_output_path.write_text(
                json.dumps(promo_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            update_payload: Dict[str, str] = {}
            if "synopsis" in missing_fields and (promo_result.get("plot_summary") or "").strip():
                update_payload["plot_summary"] = promo_result["plot_summary"]
                book_dict["synopsis"] = promo_result["plot_summary"]
            if "chapter_content" in missing_fields and (promo_result.get("chapter_content") or "").strip():
                update_payload["chapter_content"] = promo_result["chapter_content"]
                book_dict["chapter_content"] = promo_result["chapter_content"]
            if "promo_code" in missing_fields and (promo_result.get("promo_code") or "").strip():
                update_payload["promo_code"] = promo_result["promo_code"]
                book_dict["promo_code"] = promo_result["promo_code"]

            if update_payload:
                books_provider.update_promo(book.source_key, update_payload, book.synopsis)

        job_books.append(
            {
                "source_key": book.source_key,
                "title": book.title,
                "alias": book.alias,
                "platform": book.platform,
                "tags": book.tags,
                "missing_fields": missing_fields,
                "promo_query": promo_query,
                "promo": promo_result,
                "promo_error": promo_error,
            }
        )

        if steps.get("run_video", True):
            if draft_folder is None:
                video_outputs.append(
                    {
                        "source_key": book.source_key,
                        "title": book.title,
                        "result": {"status": "error", "error": "draft_folder missing"},
                    }
                )
                continue

            music_path = music_provider.pick_audio()
            output_dir = outputs_dir / safe_filename(book.title or book.alias or "book")
            result = run_video_pipeline(
                book=book_dict,
                promo_data=promo_result,
                output_dir=output_dir,
                workflow_config=workflow_config,
                system_config=system_config,
                music_path=music_path,
                draft_folder=draft_folder,
            )
            video_outputs.append(
                {"source_key": book.source_key, "title": book.title, "result": result}
            )

    job_output = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "system_config_path": str(system_config_path),
        "workflow_config_path": str(workflow_config_path),
        "books": job_books,
        "video_outputs": video_outputs,
    }
    dump_json(job_output_path, job_output)
    print(f"[OK] job output saved: {job_output_path}")

    books_provider.close()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Fetch promo info from the promotion site using a config-driven flow."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import pyperclip
from DrissionPage import ChromiumOptions, ChromiumPage

from config_utils import load_json, project_root, resolve_path

sys.stdout.reconfigure(encoding="utf-8")


def _click_copy_and_read(page: ChromiumPage, button, min_len: int = 20) -> str:
    if not button:
        return ""
    try:
        pyperclip.copy("")
        try:
            rect = button.rect()
            page.click(rect.location["x"], rect.location["y"])
        except Exception:
            button.click()
        time.sleep(1)
        text = (pyperclip.paste() or "").strip()
        return text if len(text) >= min_len else ""
    except Exception as exc:
        print(f"[WARN] Copy button failed: {exc}")
        return ""


def _clean_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("展开", "").replace("收起", "").strip()


def _looks_like_code(text: str) -> bool:
    text = (text or "").strip()
    return bool(re.fullmatch(r"[A-Za-z0-9]{4,}", text)) and any(ch.isdigit() for ch in text)


def _extract_code_from_text(text: str) -> str:
    if not text:
        return ""
    for match in re.findall(r"[A-Za-z0-9]{4,}", text):
        if any(ch.isdigit() for ch in match):
            return match
    return ""


def _safe_keyword(text: str, max_len: int = 12) -> str:
    cleaned = re.sub(r"[\"']", "", (text or "").strip())
    return cleaned[:max_len] if cleaned else ""


class PromoFetcher:
    def __init__(self, edge_config: Dict[str, object], fetch_config: Dict[str, object]) -> None:
        self.edge_config = edge_config
        self.fetch_config = fetch_config
        self.selectors = fetch_config.get("selectors", {}) if isinstance(fetch_config, dict) else {}

    def _make_page(self) -> ChromiumPage:
        edge_path = str(self.edge_config.get("edge_path", ""))
        edge_user_data = str(self.edge_config.get("edge_user_data", ""))
        edge_port = self.edge_config.get("edge_port", 9223)

        co = ChromiumOptions()
        if edge_path:
            co.set_browser_path(edge_path)
        if edge_port:
            co.set_local_port(int(edge_port))
        if edge_user_data:
            co.set_user_data_path(edge_user_data)
        return ChromiumPage(addr_or_opts=co)

    def fetch(self, book_name: str) -> Dict[str, str]:
        base_url = str(self.fetch_config.get("base_url", "")).strip()
        if not base_url:
            return {"error": "base_url missing"}

        page_load_wait = float(self.fetch_config.get("page_load_wait_sec", 2))
        post_click_wait = float(self.fetch_config.get("post_click_wait_sec", 2))
        search_wait = float(self.fetch_config.get("search_wait_sec", 3))
        promo_wait = float(self.fetch_config.get("promo_panel_wait_sec", 5))

        plot_summary = ""
        chapter_content = ""
        promo_code = ""

        page = self._make_page()
        try:
            page.get(base_url)
            time.sleep(page_load_wait)

            novel_library_selector = self.selectors.get("novel_library", "")
            if novel_library_selector:
                button = page.ele(novel_library_selector, timeout=10)
                if not button:
                    return {"error": "novel_library button not found"}
                button.click()
                time.sleep(post_click_wait)

            search_placeholder = str(self.selectors.get("search_placeholder", "")).strip()
            search_box = None
            if search_placeholder:
                search_box = page.ele(f"placeholder:{search_placeholder}", timeout=5)
                if not search_box:
                    search_box = page.ele(f"css:input[placeholder=\"{search_placeholder}\"]", timeout=5)

            if not search_box:
                inputs = page.eles("tag:input", timeout=5)
                for item in inputs:
                    placeholder = item.attr("placeholder") or ""
                    if search_placeholder and search_placeholder in placeholder:
                        search_box = item
                        break

            if not search_box:
                return {"error": "search box not found"}

            search_box.click()
            search_box.clear()
            search_box.input(book_name)
            page.run_js(
                'document.activeElement.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", keyCode: 13, bubbles: true}))'
            )
            time.sleep(search_wait)

            keyword = _safe_keyword(book_name)
            result_xpath = str(self.selectors.get("search_result_xpath", "")).format(keyword=keyword)
            if result_xpath:
                result_ele = page.ele(f"xpath:{result_xpath}", timeout=10)
            else:
                result_ele = page.ele(f"xpath://span[contains(text(), \"{keyword}\")]", timeout=10)
            if not result_ele:
                return {"error": "search result not found"}
            result_ele.click()
            time.sleep(post_click_wait)

            promo_button_text = str(self.selectors.get("promo_button_text", "")).strip()
            promo_button = page.ele(f"text:{promo_button_text}", timeout=5) if promo_button_text else None
            if not promo_button and promo_button_text:
                promo_button = page.ele(f"xpath://*[contains(text(), \"{promo_button_text}\")]", timeout=5)
            if not promo_button:
                return {"error": "promo button not found"}
            promo_button.click()
            time.sleep(promo_wait)

            plot_copy_xpath = str(self.selectors.get("plot_copy_xpath", "")).strip()
            if plot_copy_xpath:
                plot_btn = page.ele(plot_copy_xpath, timeout=3)
                plot_summary = _clean_text(_click_copy_and_read(page, plot_btn, min_len=50))

            chapter_copy_text = str(self.selectors.get("chapter_copy_text", "")).strip()
            if chapter_copy_text:
                chapter_btn = page.ele(f"text:{chapter_copy_text}", timeout=3)
                chapter_content = _clean_text(_click_copy_and_read(page, chapter_btn, min_len=80))

            promo_input_xpath = str(self.selectors.get("promo_input_xpath", "")).strip()
            if promo_input_xpath:
                promo_input = page.ele(promo_input_xpath, timeout=3)
                if promo_input:
                    promo_code = (promo_input.attr("value") or promo_input.text or "").strip()

            if not plot_summary:
                label_text = str(self.selectors.get("plot_label_text", "")).strip()
                if label_text:
                    label = page.ele(f"xpath://*[contains(text(), \"{label_text}\")]", timeout=2)
                    if label:
                        container = label.parent()
                        plot_summary = _clean_text(container.text.replace(label_text, "")) if container else ""

            if not chapter_content:
                label_text = str(self.selectors.get("chapter_label_text", "")).strip()
                if label_text:
                    label = page.ele(f"xpath://*[contains(text(), \"{label_text}\")]", timeout=2)
                    if label:
                        container = label.parent()
                        chapter_content = _clean_text(container.text.replace(label_text, "")) if container else ""

            if not _looks_like_code(promo_code):
                label_text = str(self.selectors.get("promo_label_text", "")).strip()
                if label_text:
                    label = page.ele(f"xpath://*[contains(text(), \"{label_text}\")]", timeout=2)
                    if label:
                        container = label.parent()
                        promo_code = _extract_code_from_text(container.text if container else "")

            if promo_code and not _looks_like_code(promo_code):
                promo_code = ""

            return {
                "plot_summary": plot_summary,
                "chapter_content": chapter_content,
                "promo_code": promo_code,
            }
        except Exception as exc:
            return {"error": str(exc)}
        finally:
            try:
                page.quit()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch promo info via config-driven selectors.")
    parser.add_argument("--book-name", required=True, help="Book name to search")
    parser.add_argument("--system-config", default="config/system_config.json", help="System config path")
    parser.add_argument("--output-json", default="", help="Optional JSON output path")
    args = parser.parse_args()

    root = project_root()
    system_path = resolve_path(args.system_config, root) or (root / "config/system_config.json")
    system_config = load_json(system_path)
    edge_config = system_config.get("edge", {}) if isinstance(system_config, dict) else {}
    fetch_config = system_config.get("promo_fetch", {}) if isinstance(system_config, dict) else {}

    fetcher = PromoFetcher(edge_config, fetch_config)
    result = fetcher.fetch(args.book_name)

    if args.output_json:
        output_path = resolve_path(args.output_json, root) or Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] Saved JSON: {output_path}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Reverse-prompt helper: use Doubao vision models to draft Jimeng prompts."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    stripped = text.strip()
    # Common case: markdown fenced JSON.
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    # Try direct parse first.
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    # Fallback: extract first JSON object span.
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = stripped[start : end + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _to_data_url(image_path: Path) -> str:
    content = image_path.read_bytes()
    mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    b64 = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{b64}"


def resolve_reference_images(raw: object, base_dir: Path) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, (str, Path)):
        items = [str(raw)]
    elif isinstance(raw, Iterable):
        items = [str(item) for item in raw if str(item).strip()]
    else:
        return []

    results: List[str] = []
    for value in items:
        value = value.strip()
        if not value:
            continue
        if value.startswith("http://") or value.startswith("https://"):
            results.append(value)
            continue
        path = Path(value)
        if not path.is_absolute():
            path = base_dir / path
        results.append(str(path))
    return results


@dataclass
class DoubaoVisionConfig:
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    model: str = "doubao-seed-1-6-vision-250815"
    api_key: str = ""
    api_key_env: str = "ARK_API_KEY"
    timeout_sec: int = 120
    max_retries: int = 1

    def resolved_api_key(self) -> str:
        key = (self.api_key or "").strip()
        if key:
            return key
        if self.api_key_env:
            return (os.environ.get(self.api_key_env) or "").strip()
        return ""

    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")


class DoubaoVisionPromptExtractor:
    """Call Doubao vision chat completion and return a Jimeng-oriented prompt pack."""

    def __init__(self, config: DoubaoVisionConfig) -> None:
        self.config = config

    def _build_messages(
        self,
        image_urls: Sequence[str],
        style_preset: str,
        target_aspect_ratio: str,
        target_model: str,
        language: str,
        extra_instruction: str,
    ) -> List[Dict[str, Any]]:
        system_prompt = (
            "You are a senior creative director for short-video production. "
            "Your task is to reverse-engineer visual style from reference images "
            "and output a high-quality prompt for Jimeng image generation."
        )

        user_rules = (
            "Analyze the reference images and output STRICT JSON only, no markdown, "
            "no extra prose.\n"
            "JSON schema:\n"
            "{\n"
            '  "summary": "one-paragraph style summary",\n'
            '  "scene_elements": ["..."],\n'
            '  "camera_language": "shot type, lens, framing, motion sense",\n'
            '  "lighting_color": "lighting and palette details",\n'
            '  "subject_details": "identity + outfit + pose + expression",\n'
            '  "jimeng_prompt": "final positive prompt for Jimeng",\n'
            '  "jimeng_negative_prompt": "negative prompt for Jimeng",\n'
            '  "confidence": 0.0\n'
            "}\n"
            f"Target style preset: {style_preset or 'generic'}.\n"
            f"Target aspect ratio: {target_aspect_ratio or '9:16'}.\n"
            f"Target generator: {target_model or 'jimeng-4.5'}.\n"
            f"Output language for text fields: {language or 'zh'}.\n"
            "Focus on actionable visual keywords, not abstract theory.\n"
        )
        if extra_instruction:
            user_rules += f"Extra instruction: {extra_instruction.strip()}\n"

        user_content: List[Dict[str, Any]] = [{"type": "text", "text": user_rules}]
        for url in image_urls:
            user_content.append({"type": "image_url", "image_url": {"url": url}})

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _normalize_image_inputs(self, images: Sequence[str]) -> List[str]:
        normalized: List[str] = []
        for item in images:
            raw = str(item or "").strip()
            if not raw:
                continue
            if raw.startswith("http://") or raw.startswith("https://"):
                normalized.append(raw)
                continue
            path = Path(raw)
            if not path.exists() or not path.is_file():
                raise FileNotFoundError(f"Reference image not found: {path}")
            normalized.append(_to_data_url(path))
        return normalized

    def infer_prompt(
        self,
        reference_images: Sequence[str],
        style_preset: str = "generic",
        target_aspect_ratio: str = "9:16",
        target_model: str = "jimeng-4.5",
        language: str = "zh",
        extra_instruction: str = "",
        max_reference_images: int = 3,
    ) -> Dict[str, Any]:
        api_key = self.config.resolved_api_key()
        if not api_key:
            raise ValueError(
                "Doubao API key missing. Set system_config.doubao_vision.api_key "
                "or export ARK_API_KEY."
            )

        images = [str(x) for x in reference_images if str(x).strip()]
        if not images:
            raise ValueError("reference_images is empty")

        cap = max(1, int(max_reference_images or 3))
        clipped_inputs = images[:cap]
        image_urls = self._normalize_image_inputs(clipped_inputs)

        messages = self._build_messages(
            image_urls=image_urls,
            style_preset=style_preset,
            target_aspect_ratio=target_aspect_ratio,
            target_model=target_model,
            language=language,
            extra_instruction=extra_instruction,
        )

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1200,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.config.normalized_base_url()}/chat/completions"

        last_error = ""
        retries = max(0, int(self.config.max_retries))
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=int(self.config.timeout_sec or 120),
                )
                response.raise_for_status()
                data = response.json()

                choices = data.get("choices") if isinstance(data, dict) else None
                if not choices:
                    raise RuntimeError(f"No choices in response: {data}")

                message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
                content = message.get("content", "")
                if isinstance(content, list):
                    parts = []
                    for part in content:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            parts.append(part["text"])
                    content_text = "\n".join(parts).strip()
                else:
                    content_text = str(content or "").strip()

                parsed = _extract_json_object(content_text)
                if not parsed:
                    # Keep a permissive fallback so pipeline still works.
                    parsed = {
                        "summary": content_text,
                        "jimeng_prompt": content_text,
                        "jimeng_negative_prompt": "",
                        "confidence": 0.2,
                    }

                return {
                    "provider": "doubao_vision",
                    "model": self.config.model,
                    "created_at": _utc_now_iso(),
                    "reference_images": clipped_inputs,
                    "raw_content": content_text,
                    "structured": parsed,
                    "jimeng_prompt": str(parsed.get("jimeng_prompt") or "").strip(),
                    "jimeng_negative_prompt": str(parsed.get("jimeng_negative_prompt") or "").strip(),
                }
            except Exception as exc:
                last_error = str(exc)
                if attempt >= retries:
                    break

        raise RuntimeError(f"Doubao reverse prompt failed: {last_error}")


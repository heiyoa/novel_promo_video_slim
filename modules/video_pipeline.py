# -*- coding: utf-8 -*-
"""Video pipeline orchestration."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from doubao_vision_prompt import (
    DoubaoVisionConfig,
    DoubaoVisionPromptExtractor,
    resolve_reference_images,
)
from jimeng_image_generator import JimengImageGenerator
from novel_rewriter import NovelRewriter
from script_to_subtitle import ScriptToSubtitle
from utils import build_novel_text, contains_cjk, safe_draft_name, safe_filename


def ensure_sys_path(path: Path) -> None:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def parse_export_enum(value: str, enum_cls, prefix: str):
    if not value:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    normalized_no_fps = normalized.replace("FPS", "")
    for item in enum_cls:
        name_key = item.name.upper()
        value_key = item.value.upper()
        short_key = name_key.replace(prefix, "")
        value_no_fps = value_key.replace("FPS", "")
        candidates = {name_key, value_key, short_key, value_no_fps}
        if normalized in candidates or normalized_no_fps in candidates:
            return item
    return None


def _prepare_image_prompt(
    workflow_config: Dict[str, object],
    system_config: Dict[str, object],
    output_dir: Path,
) -> Tuple[str, str, Dict[str, str]]:
    mode = str(workflow_config.get("image_prompt_mode") or "manual").strip().lower()
    manual_prompt = str(workflow_config.get("image_prompt") or "").strip()
    manual_negative = str(workflow_config.get("image_negative_prompt") or "").strip()
    extra_result: Dict[str, str] = {}

    if mode != "doubao_reverse":
        return manual_prompt, manual_negative, extra_result

    reverse_cfg = workflow_config.get("prompt_reverse", {})
    reverse_cfg = reverse_cfg if isinstance(reverse_cfg, dict) else {}
    reference_images = resolve_reference_images(
        workflow_config.get("reference_images"),
        Path(__file__).resolve().parents[1],
    )
    if not reference_images:
        if manual_prompt:
            extra_result["prompt_reverse_note"] = (
                "image_prompt_mode=doubao_reverse but reference_images is empty, fallback to manual image_prompt"
            )
            return manual_prompt, manual_negative, extra_result
        return "", "", {"prompt_reverse_error": "reference_images is empty"}

    vision_cfg_raw = system_config.get("doubao_vision", {})
    vision_cfg_raw = vision_cfg_raw if isinstance(vision_cfg_raw, dict) else {}
    vision_cfg = DoubaoVisionConfig(
        base_url=str(vision_cfg_raw.get("base_url") or "https://ark.cn-beijing.volces.com/api/v3").strip(),
        model=str(vision_cfg_raw.get("model") or "doubao-seed-1-6-vision-250815").strip(),
        api_key=str(vision_cfg_raw.get("api_key") or "").strip(),
        api_key_env=str(vision_cfg_raw.get("api_key_env") or "ARK_API_KEY").strip(),
        timeout_sec=int(vision_cfg_raw.get("timeout_sec") or 120),
        max_retries=int(vision_cfg_raw.get("max_retries") or 1),
    )

    extractor = DoubaoVisionPromptExtractor(vision_cfg)
    result = extractor.infer_prompt(
        reference_images=reference_images,
        style_preset=str(reverse_cfg.get("style_preset") or "generic"),
        target_aspect_ratio=str(reverse_cfg.get("target_aspect_ratio") or "9:16"),
        target_model=str(reverse_cfg.get("target_model") or "jimeng-4.5"),
        language=str(reverse_cfg.get("language") or "zh"),
        extra_instruction=str(reverse_cfg.get("extra_instruction") or "").strip(),
        max_reference_images=int(reverse_cfg.get("max_reference_images") or 3),
    )

    reverse_report_path = output_dir / "prompt_reverse_result.json"
    reverse_report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    extra_result["prompt_reverse_report"] = str(reverse_report_path)

    inferred_prompt = str(result.get("jimeng_prompt") or "").strip()
    inferred_negative = str(result.get("jimeng_negative_prompt") or "").strip()
    final_prompt = inferred_prompt or manual_prompt
    final_negative = manual_negative or inferred_negative

    if not inferred_prompt and manual_prompt:
        extra_result["prompt_reverse_note"] = (
            "Doubao reverse prompt returned empty jimeng_prompt, fallback to manual image_prompt"
        )
    return final_prompt, final_negative, extra_result


def export_draft_video(
    pyjy_root: Path,
    draft_name: str,
    output_dir: Path,
    title: str,
    alias: str,
    jianying_config: Dict[str, object],
) -> Dict[str, str]:
    auto_export = bool(jianying_config.get("auto_export"))
    if not auto_export:
        return {"status": "skipped"}

    if not pyjy_root.exists():
        return {"status": "error", "error": f"pyJianYingDraft missing: {pyjy_root}"}

    ensure_sys_path(pyjy_root)
    try:
        from pyJianYingDraft import JianyingController, ExportResolution, ExportFramerate
    except Exception as exc:
        return {"status": "error", "error": f"export module load failed: {exc}"}

    exe_path_value = str(jianying_config.get("exe_path") or "").strip()
    exe_path = Path(exe_path_value) if exe_path_value else None
    auto_launch = bool(jianying_config.get("auto_launch", True))
    launch_wait_sec = int(jianying_config.get("launch_wait_sec", 15))

    export_dir_value = str(jianying_config.get("export_dir") or "").strip()
    export_dir = Path(export_dir_value) if export_dir_value else output_dir
    export_dir.mkdir(parents=True, exist_ok=True)

    export_base = alias if contains_cjk(alias) else (title or alias or draft_name)
    export_name = safe_filename(export_base)
    export_path = export_dir / f"{export_name}.mp4"

    overwrite = bool(jianying_config.get("export_overwrite", True))
    if export_path.exists():
        if overwrite:
            export_path.unlink()
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = export_path.with_name(f"{export_path.stem}_{stamp}{export_path.suffix}")

    resolution_value = str(jianying_config.get("export_resolution") or "").strip()
    framerate_value = str(jianying_config.get("export_framerate") or "").strip()
    resolution = parse_export_enum(resolution_value, ExportResolution, "RES_")
    framerate = parse_export_enum(framerate_value, ExportFramerate, "FR_")

    timeout = jianying_config.get("export_timeout_sec", 1200)
    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        timeout = 1200

    try:
        controller = JianyingController()
    except Exception as exc:
        if not (auto_launch and exe_path):
            return {"status": "error", "error": f"Jianying window not found: {exc}"}
        if exe_path is None or not exe_path.exists():
            return {"status": "error", "error": f"Jianying path missing: {exe_path}"}
        try:
            subprocess.Popen([str(exe_path)])
        except Exception as launch_exc:
            return {"status": "error", "error": f"Jianying launch failed: {launch_exc}"}
        time.sleep(launch_wait_sec)
        controller = JianyingController()

    try:
        controller.export_draft(
            draft_name,
            str(export_path),
            resolution=resolution,
            framerate=framerate,
            timeout=timeout,
        )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    return {"status": "ok", "export_path": str(export_path)}


def run_video_pipeline(
    book: Dict[str, str],
    promo_data: Dict[str, str],
    output_dir: Path,
    workflow_config: Dict[str, object],
    system_config: Dict[str, object],
    music_path: Optional[Path],
    draft_folder: Path,
) -> Dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    novel_text_priority = workflow_config.get("novel_text_priority", []) or []
    novel_text = build_novel_text(book, promo_data, novel_text_priority)
    if not novel_text:
        return {"status": "error", "error": "missing novel text"}

    novel_input_path = output_dir / "novel_input.txt"
    novel_input_path.write_text(novel_text, encoding="utf-8")

    rewrite_prompt = str(workflow_config.get("rewrite_prompt") or "").strip()
    llm_config = system_config.get("llm", {}) if isinstance(system_config, dict) else {}

    rewriter = NovelRewriter(
        api_key=str(llm_config.get("api_key") or "").strip(),
        api_endpoint=str(llm_config.get("api_endpoint") or "").strip(),
        model_name=str(llm_config.get("model") or "").strip() or None,
        model_fallbacks=llm_config.get("model_fallbacks") or None,
    )

    script_text = rewriter.rewrite_novel(novel_text, prompt_override=rewrite_prompt)
    if not script_text:
        return {"status": "error", "error": "rewrite failed"}

    script_md_path = output_dir / "script.md"
    script_json_path = output_dir / "script.json"
    script_md_path.write_text(script_text, encoding="utf-8")
    script_data = rewriter.parse_script(script_text)
    script_json_path.write_text(
        json.dumps(script_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    converter = ScriptToSubtitle()
    if not converter.load_script(str(script_md_path)):
        return {"status": "error", "error": "script parse failed"}

    srt_path = output_dir / "subtitles.srt"
    if not converter.generate_subtitle(str(srt_path)):
        return {"status": "error", "error": "subtitle generation failed"}

    extra_result: Dict[str, Any] = {}
    try:
        image_prompt, negative_prompt, prompt_meta = _prepare_image_prompt(
            workflow_config=workflow_config,
            system_config=system_config,
            output_dir=output_dir,
        )
        if prompt_meta:
            extra_result.update(prompt_meta)
    except Exception as exc:
        return {"status": "error", "error": f"reverse prompt failed: {exc}"}

    if not image_prompt:
        return {"status": "error", "error": "image_prompt missing"}

    jimeng_config = system_config.get("jimeng", {}) if isinstance(system_config, dict) else {}
    session_id = str(jimeng_config.get("session_id") or "").strip()
    if not session_id:
        return {"status": "error", "error": "jimeng session_id missing"}

    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    generator = JimengImageGenerator(
        session_id=session_id,
        output_dir=str(image_dir),
        model=jimeng_config.get("model") or "JIMENG_4_5",
        ratio=jimeng_config.get("ratio") or "RATIO_9_16",
        resolution=jimeng_config.get("resolution") or "RESOLUTION_2K",
        debug=bool(jimeng_config.get("debug", False)),
        timeout_sec=int(jimeng_config.get("timeout_sec", 45)),
        verify_tls=bool(jimeng_config.get("verify_tls", False)),
    )

    image_path = generator.generate_base_image(image_prompt, negative_prompt)
    if not image_path:
        return {"status": "error", "error": "image generation failed"}

    if not music_path:
        return {"status": "error", "error": "music file missing"}
    if not draft_folder.exists():
        return {"status": "error", "error": f"draft folder missing: {draft_folder}"}

    title = book.get("title", "") or ""
    alias = book.get("alias", "") or ""
    draft_base = alias if contains_cjk(alias) else (title or alias)
    draft_name = safe_draft_name(draft_base or "NovelPromoVideo")
    jianying_config = system_config.get("jianying", {}) if isinstance(system_config, dict) else {}
    prefix = str(jianying_config.get("draft_name_prefix") or "").strip()
    if prefix:
        draft_name = f"{prefix}{draft_name}"

    video_config = workflow_config.get("video", {}) if isinstance(workflow_config, dict) else {}

    from video_composer import create_video_from_srt

    draft_output_path = output_dir / "draft.json"
    ok = create_video_from_srt(
        str(srt_path),
        str(image_path),
        str(music_path),
        str(draft_output_path),
        str(draft_folder),
        draft_name=draft_name,
        audio_volume=float(video_config.get("audio_volume", 0.3)),
        font_name=str(video_config.get("font", "挥墨体")),
        font_size=int(video_config.get("font_size", 15)),
        letter_spacing=int(video_config.get("letter_spacing", 0)),
        line_spacing=int(video_config.get("line_spacing", 7)),
        bold=bool(video_config.get("bold", True)),
        auto_wrapping=bool(video_config.get("auto_wrapping", True)),
    )
    if not ok:
        return {"status": "error", "error": "draft generation failed"}

    pyjy_root = Path(__file__).resolve().parent / "pyJianYingDraft-main"
    export_result = export_draft_video(
        pyjy_root=pyjy_root,
        draft_name=draft_name,
        output_dir=output_dir,
        title=title,
        alias=alias,
        jianying_config=jianying_config,
    )
    if export_result.get("status") == "error":
        return {
            "status": "error",
            "error": "auto export failed",
            "draft_output": str(draft_output_path),
            "draft_name": draft_name,
            "export": export_result,
        }

    result: Dict[str, Any] = {
        "status": "ok",
        "novel_input": str(novel_input_path),
        "script_md": str(script_md_path),
        "script_json": str(script_json_path),
        "subtitle": str(srt_path),
        "image": str(image_path),
        "music": str(music_path),
        "draft_output": str(draft_output_path),
        "draft_name": draft_name,
        "export": export_result,
        "image_prompt_final": image_prompt,
        "image_negative_prompt_final": negative_prompt,
    }
    if extra_result:
        result.update(extra_result)
    return result

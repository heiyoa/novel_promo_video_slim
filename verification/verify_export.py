#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only post-export technical verification for novel_promo_video_slim.

Verdict semantics (fail-closed):
  PASS    all frozen necessary technical checks satisfied for the exact artifact SHA-256
  FAIL    the artifact was evaluated and at least one necessary frozen check failed
  UNKNOWN evaluation was not possible (missing file/dependency, unreadable path,
          invalid criteria) or evidence was insufficient

This tool never re-exports, overwrites the input, launches GUIs, publishes, or
evaluates professional/business quality (E2/E3/E4 stay NOT_EVALUATED).

Usage:
  python verification/verify_export.py <video_path> [--json-out PATH] [--criteria PATH]

Exit codes: 0 = PASS, 1 = FAIL, 2 = UNKNOWN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "novel_promo_video_slim.export_technical_verdict/v1"
TOOL_VERSION = "verify_export.py 1.0"
DEFAULT_CRITERIA = Path(__file__).resolve().parent / "frozen_criteria.json"
REQUIRED_CRITERIA_KEYS = ("min_duration_s", "min_width", "min_height", "audio_policy")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for chunk in iter(lambda: fd.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(argv: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, check=False)


def check(name: str, ok: bool, **details) -> dict:
    return {"id": name, "pass": bool(ok), **details}


def unknown_result(media: Path, criteria_ref: str, reason: str) -> dict:
    return {
        "schema": SCHEMA, "tool_version": TOOL_VERSION, "created_at": iso_now(),
        "verdict": "UNKNOWN", "unknown_reason": reason,
        "media_path": str(media), "media_sha256": None,
        "criteria_ref": criteria_ref, "criteria_sha256": None,
        "checks": [], "attributes": {}, "sample_frames": [], "elapsed_s": None,
        "professional_status": "NOT_EVALUATED",
        "business_status": "NOT_EVALUATED",
        "publishing_authorization": "NONE",
    }


def load_criteria(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf8"))
    if not isinstance(data, dict):
        raise ValueError("criteria root must be an object")
    minimums = data.get("e1_technical_minimum")
    if not isinstance(minimums, dict) or any(k not in minimums for k in REQUIRED_CRITERIA_KEYS):
        raise ValueError("criteria missing e1_technical_minimum keys")
    if minimums["audio_policy"] not in ("REQUIRED", "OPTIONAL", "FORBIDDEN"):
        raise ValueError("bad audio_policy")
    return data


def verify_media(media: Path, criteria: dict, criteria_sha: str, criteria_ref: str,
                 decode_timeout: int = 180) -> dict:
    """Every necessary check is fail-closed; verdict is PASS only if all pass."""
    minimums = criteria["e1_technical_minimum"]
    start = time.monotonic()
    result = {
        "schema": SCHEMA, "tool_version": TOOL_VERSION, "created_at": iso_now(),
        "verdict": "UNKNOWN", "unknown_reason": None,
        "media_path": str(media), "media_sha256": None,
        "criteria_ref": criteria_ref, "criteria_sha256": criteria_sha,
        "checks": [], "attributes": {}, "sample_frames": [], "elapsed_s": None,
        "professional_status": "NOT_EVALUATED",
        "business_status": "NOT_EVALUATED",
        "publishing_authorization": "NONE",
    }
    checks = result["checks"]

    if not media.exists():
        result["unknown_reason"] = "media_not_found"
        return result
    try:
        size = media.stat().st_size
    except OSError as exc:
        result["unknown_reason"] = f"media_unreadable: {exc}"[:250]
        return result
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        result["unknown_reason"] = "ffprobe_or_ffmpeg_not_on_path"
        return result

    checks.append(check("media_nonempty", size > 0, bytes=size))
    if size == 0:
        result["verdict"] = "FAIL"
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        return result
    result["media_sha256"] = sha256_file(media)

    try:
        proc = run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                    "-of", "json", str(media)], timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["unknown_reason"] = f"ffprobe_failed_to_run: {exc}"[:250]
        return result
    if proc.returncode != 0:
        checks.append(check("ffprobe_video_stream", False,
                            error=proc.stderr.decode("utf8", "replace")[-250:]))
        result["verdict"] = "FAIL"
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        return result
    try:
        probe = json.loads(proc.stdout)
    except ValueError:
        result["unknown_reason"] = "ffprobe_output_unparsable"
        return result
    streams = probe.get("streams") or []
    fmt = probe.get("format") or {}
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    checks.append(check("ffprobe_video_stream", bool(videos)))
    if not videos:
        result["verdict"] = "FAIL"
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        return result

    stream = videos[0]
    duration = float(fmt.get("duration") or stream.get("duration") or 0)
    width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
    result["attributes"] = {
        "duration_s": duration, "width": width, "height": height,
        "video_codec": stream.get("codec_name"), "has_audio": bool(audios),
        "audio_streams": len(audios), "bytes": size,
    }
    checks.append(check("minimum_duration", duration >= float(minimums["min_duration_s"]),
                        actual=duration, required=minimums["min_duration_s"]))
    checks.append(check("minimum_dimensions",
                        width >= int(minimums["min_width"]) and height >= int(minimums["min_height"]),
                        width=width, height=height))
    if minimums.get("vertical_format_required"):
        checks.append(check("vertical_format", height > width, width=width, height=height))
    policy = minimums["audio_policy"]
    checks.append(check("audio_policy",
                        policy == "OPTIONAL" or (policy == "REQUIRED" and bool(audios))
                        or (policy == "FORBIDDEN" and not audios),
                        requirement=policy, has_audio=bool(audios)))

    try:
        proc = run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-xerror",
                    "-i", str(media), "-map", "0:v:0", "-f", "null", "-"],
                   timeout=decode_timeout)
        checks.append(check("full_video_decode", proc.returncode == 0,
                            error=proc.stderr.decode("utf8", "replace")[-250:]))
    except (OSError, subprocess.TimeoutExpired) as exc:
        checks.append(check("full_video_decode", False, error=str(exc)[:250]))

    if criteria.get("extract_frames", True) is not False:
        frames_ok = []
        with tempfile.TemporaryDirectory(prefix="export-verify-") as folder:
            for frac in (0.15, 0.5, 0.85):
                t = max(0.0, min(duration - 0.05, duration * frac))
                img = Path(folder) / f"frame_{int(frac*100)}.png"
                try:
                    proc = run(["ffmpeg", "-nostdin", "-v", "error", "-y",
                                "-ss", f"{t:.4f}", "-i", str(media), "-frames:v", "1",
                                str(img)], timeout=60)
                    ok = proc.returncode == 0 and img.exists() and img.stat().st_size > 0
                except (OSError, subprocess.TimeoutExpired):
                    ok = False
                frames_ok.append(ok)
                result["sample_frames"].append({"fraction": frac, "time_s": round(t, 3),
                                                "ok": ok, "sha256": sha256_file(img) if ok else None})
        checks.append(check("three_frames_decodable", all(frames_ok)))

    result["verdict"] = "PASS" if checks and all(c["pass"] for c in checks) else "FAIL"
    result["elapsed_s"] = round(time.monotonic() - start, 3)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only export technical verifier (PASS/FAIL/UNKNOWN)")
    ap.add_argument("media", type=Path)
    ap.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)

    try:
        criteria = load_criteria(args.criteria)
        criteria_sha = sha256_file(args.criteria)
        criteria_ref = str(args.criteria)
    except (OSError, ValueError) as exc:
        result = unknown_result(args.media, str(args.criteria), f"criteria_invalid: {exc}"[:250])
        print(json.dumps(result, ensure_ascii=False))
        return 2

    result = verify_media(args.media, criteria, criteria_sha, criteria_ref)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf8")
    print(json.dumps({k: result[k] for k in
                      ("verdict", "media_sha256", "unknown_reason", "elapsed_s")},
                     ensure_ascii=False))
    return {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())

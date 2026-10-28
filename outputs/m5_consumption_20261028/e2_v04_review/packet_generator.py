#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off E2 evidence packet generator for M5 v0.4 professional review.

Reads only: script.md / subtitles.srt / draft.json / exported MP4s of this project.
Writes: structured evidence JSONs + per-cue midpoint storyboard frames + audio
technical facts. Claims no full-video playback and no audio content judgment.
Original material SHAs are preserved and never modified.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # outputs/ (video + per-run artifact dirs live here)
OUT = Path(__file__).resolve().parent
NOW = datetime.now(timezone.utc).isoformat()

ARTIFACTS = {
    "love_hidden": {
        "video": "exported_videos/Love_Hidden_in_Dreams.mp4",
        "script_md": "Love_Hidden_in_Dreams/script.md",
        "srt": "Love_Hidden_in_Dreams/subtitles.srt",
        "draft_json": "Love_Hidden_in_Dreams/draft.json",
        "script_json": "Love_Hidden_in_Dreams/script.json",
    },
    "fitness_reset": {
        "video": "exported_videos/Fitness_Reset.mp4",
        "script_md": "Fitness_Reset_20260209_003506/script.md",
        "srt": "Fitness_Reset_20260209_003506/subtitles.srt",
        "draft_json": "Fitness_Reset_20260209_003506/draft.json",
        "script_json": None,
    },
}

GITHUB_MAIN_BLOBS = {
    "Love_Hidden_in_Dreams/script.md": "9ed0119f1faad6b2de10a362d6777520771ef235",
    "Love_Hidden_in_Dreams/draft.json": "3c078b8b9cbca17384561aa8a976243a649ba90e",
    "Love_Hidden_in_Dreams/subtitles.srt": "2985a37f2e0059648a749bcc8842223261c6cdc5",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_blob_sha(p: Path) -> str:
    b = p.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def parse_srt(p: Path) -> list[dict]:
    cues = []
    for block in re.split(r"\n\s*\n", p.read_text(encoding="utf-8-sig").strip()):
        lines = block.strip().splitlines()
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1])
        t = lambda h, mi, s, ms: int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000
        start = t(*m.group(1, 2, 3, 4))
        end = t(*m.group(5, 6, 7, 8))
        text = "\n".join(lines[2:]).strip()
        chars = len(text)
        cues.append({"index": len(cues) + 1, "start_s": round(start, 3), "end_s": round(end, 3),
                     "duration_s": round(end - start, 3), "chars": chars,
                     "chars_per_sec": round(chars / (end - start), 2) if end > start else None,
                     "text": text})
    return cues


def parse_script_md(p: Path) -> list[dict]:
    slides = []
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        # slide rows look like "| **1** | text | scene | 6s |" or "| 1 | text | scene | 3s |"
        if re.match(r"^\|\s*\*{0,2}\d+\*{0,2}\s*\|", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and cells[1] and cells[2]:
                slides.append({"slide": cells[0].strip("*"),
                               "overlay_text": cells[1],
                               "visual_scene": cells[2],
                               "planned_duration_s": cells[3]})
    return slides


def ffprobe_attrs(video: Path) -> dict:
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(video)], stdout=subprocess.PIPE, check=True)
    probe = json.loads(proc.stdout)
    streams = probe["streams"]
    v = [s for s in streams if s["codec_type"] == "video"][0]
    a = [s for s in streams if s["codec_type"] == "audio"]
    return {"duration_s": float(probe["format"]["duration"]), "width": v["width"],
            "height": v["height"], "video_codec": v["codec_name"],
            "audio_streams": len(a), "audio_codec": a[0]["codec_name"] if a else None,
            "video_sha256": sha256_file(video)}


def scene_changes(video: Path, threshold: float = 0.2) -> list[float]:
    proc = subprocess.run(["ffmpeg", "-nostdin", "-i", str(video),
                           "-vf", f"select='gt(scene,{threshold})',showinfo",
                           "-f", "null", "-"], stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    times = re.findall(r"pts_time:([\d.]+)", proc.stderr.decode("utf8", "replace"))
    return sorted({round(float(t), 3) for t in times})


def audio_facts(video: Path) -> dict:
    out = {}
    proc = subprocess.run(["ffmpeg", "-nostdin", "-i", str(video), "-map", "0:a:0",
                           "-af", "volumedetect", "-f", "null", "-"],
                          stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    err = proc.stderr.decode("utf8", "replace")
    mean = re.search(r"mean_volume: ([-\d.]+) dB", err)
    mx = re.search(r"max_volume: ([-\d.]+) dB", err)
    out["mean_volume_db"] = float(mean.group(1)) if mean else None
    out["max_volume_db"] = float(mx.group(1)) if mx else None
    proc = subprocess.run(["ffmpeg", "-nostdin", "-i", str(video), "-map", "0:a:0",
                           "-af", "silencedetect=noise=-35dB:d=2", "-f", "null", "-"],
                          stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
    err = proc.stderr.decode("utf8", "replace")
    silences = re.findall(r"silence_start: ([\d.]+)", err)
    out["silence_segments_over_2s_at_-35dB"] = len(silences)
    out["note"] = ("Technical signal facts only. Audio CONTENT (music genre, lyrics, "
                   "sync feel) is UNKNOWN: this review cannot listen.")
    return out


def draft_facts(p: Path) -> dict:
    d = json.loads(p.read_text(encoding="utf-8-sig"))
    mats = d["materials"]
    vids = [{"name": v.get("material_name"), "path_last2": "\\\\".join((v.get("path") or "").split("\\\\")[-2:]),
             "type": v.get("type"), "w": v.get("width"), "h": v.get("height")} for v in mats["videos"]]
    auds = [{"name": a.get("name")} for a in mats["audios"]]
    return {"canvas": [d["canvas_config"]["width"], d["canvas_config"]["height"]],
            "duration_s": round(d["duration"] / 1e6, 3),
            "video_materials": vids, "audio_materials": auds,
            "text_materials": len(mats["texts"]),
            "transitions": len(mats["transitions"]), "effects": len(mats["effects"]),
            "track_segments": {t["type"]: len(t["segments"]) for t in d["tracks"]}}


def map_cues_to_slides(cues: list[dict], slides: list[dict]) -> list[dict]:
    """Assign each cue to a script slide by longest common substring on normalized text."""
    def norm(s: str) -> str:
        return re.sub(r"[^a-z]+", "", s.lower())
    mapping = []
    slide_norms = [norm(s["overlay_text"]) for s in slides]
    for cue in cues:
        c = norm(cue["text"])
        best, score = None, -1
        for i, sn in enumerate(slide_norms):
            # count cue chars present in slide text (order-free containment proxy)
            if not c:
                continue
            shared = sum(1 for tok in re.split(r"(?<=.)(?=[A-Z])| ", cue["text"]) if norm(tok) and norm(tok) in sn)
            if shared > score:
                best, score = i, shared
        mapping.append({"cue": cue["index"], "slide": slides[best]["slide"] if best is not None and score > 0 else None})
    return mapping


def extract_frame(video: Path, t: float, out: Path, width: int = 360) -> None:
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}",
                    "-i", str(video), "-frames:v", "1", "-vf", f"scale={width}:-1",
                    "-q:v", "5", str(out)], check=True)


def main() -> None:
    manifest = {"schema": "m5.e2_evidence_packet/v1", "generated_at": NOW,
                "github_main_blobs_expected": GITHUB_MAIN_BLOBS, "artifacts": {}}
    for key, refs in ARTIFACTS.items():
        entry: dict = {}
        for label, rel in refs.items():
            if rel is None:
                continue
            p = ROOT / rel
            entry[label] = {"path": rel, "sha256": sha256_file(p),
                            "git_blob_normalized": git_blob_sha(p),
                            "bytes": p.stat().st_size}
            if rel in GITHUB_MAIN_BLOBS:
                entry[label]["matches_github_main_blob"] = git_blob_sha(p) == GITHUB_MAIN_BLOBS[rel]
        video = ROOT / refs["video"]
        entry["probe"] = ffprobe_attrs(video)
        cues = parse_srt(ROOT / refs["srt"])
        slides = parse_script_md(ROOT / refs["script_md"])
        draft = draft_facts(ROOT / refs["draft_json"])
        srt_stats = {"cue_count": len(cues), "max_chars": max(c["chars"] for c in cues),
                     "max_duration_s": max(c["duration_s"] for c in cues),
                     "max_chars_per_sec": max(c["chars_per_sec"] for c in cues),
                     "cues": cues}
        intent = {"script_slide_count": len(slides), "slides": slides,
                  "draft_video_material_count": len(draft["video_materials"]),
                  "slide_cue_mapping": map_cues_to_slides(cues, slides),
                  "planned_total_duration_s": sum(
                      float(s["planned_duration_s"].rstrip("s")) for s in slides if s["planned_duration_s"].endswith("s")),
                  "actual_duration_s": entry["probe"]["duration_s"]}
        frames_dir = OUT / f"storyboard_{key}"
        frames_dir.mkdir(exist_ok=True)
        frame_files = []
        for cue in cues:
            mid = round((cue["start_s"] + cue["end_s"]) / 2, 3)
            f = frames_dir / f"cue{cue['index']:02d}_t{mid:.2f}.jpg"
            extract_frame(video, mid, f)
            frame_files.append({"cue": cue["index"], "midpoint_s": mid, "file": f.name,
                                "sha256": sha256_file(f)})
        sc = scene_changes(video)
        af = audio_facts(video)
        entry["evidence"] = {"srt_stats": srt_stats, "intent_gap": intent,
                             "draft_facts": draft, "scene_changes_detected": sc,
                             "scene_change_note": ("visual transitions detected at listed times; "
                                                   "empty list means no cut above 0.2 threshold — "
                                                   "consistent with a static-photo draft"),
                             "audio_tech_facts": af,
                             "storyboard": frame_files}
        manifest["artifacts"][key] = entry
    (OUT / "evidence_packet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    print(json.dumps({k: {"slides": v["evidence"]["intent_gap"]["script_slide_count"],
                          "video_materials": v["evidence"]["intent_gap"]["draft_video_material_count"],
                          "cues": v["evidence"]["srt_stats"]["cue_count"],
                          "max_cps": v["evidence"]["srt_stats"]["max_chars_per_sec"],
                          "scene_changes": len(v["evidence"]["scene_changes_detected"]),
                          "blob_matches": all(x.get("matches_github_main_blob") for x in v.values() if isinstance(x, dict))}
                      for k, v in manifest["artifacts"].items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

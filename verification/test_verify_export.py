# -*- coding: utf-8 -*-
"""Negative controls and positive control for verification/verify_export.py.

Deterministic, local-only. ffmpeg-dependent tests are skipped when ffmpeg is absent.
A FAIL verdict here must never be readable as professional or business success:
the verdict object carries professional_status/business_status = NOT_EVALUATED.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_export  # noqa: E402

FFMPEG = shutil.which("ffmpeg") is not None
CRITERIA = verify_export.load_criteria(verify_export.DEFAULT_CRITERIA)
CRITERIA_SHA = verify_export.sha256_file(verify_export.DEFAULT_CRITERIA)


def make_synthetic(path: Path, *, width: int = 720, height: int = 1280,
                   seconds: float = 6.0, audio: bool = True) -> None:
    src = "testsrc=size=%dx%d:rate=15:duration=%s" % (width, height, seconds)
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", src]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=%s" % seconds]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [str(path)]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class ExportVerificationTests(unittest.TestCase):
    def result_for(self, media: Path) -> dict:
        return verify_export.verify_media(media, CRITERIA, CRITERIA_SHA, "test-criteria")

    def test_missing_file_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.result_for(Path(tmp) / "nope.mp4")
        self.assertEqual(result["verdict"], "UNKNOWN")
        self.assertEqual(result["unknown_reason"], "media_not_found")
        self.assertIsNone(result["media_sha256"])

    def test_empty_file_is_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "empty.mp4"
            media.write_bytes(b"")
            result = self.result_for(media)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(any(c["id"] == "media_nonempty" and not c["pass"]
                            for c in result["checks"]))

    def test_garbage_bytes_is_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "garbage.mp4"
            media.write_bytes(b"\x00\x01\x02not-a-video" * 100)
            result = self.result_for(media)
        self.assertEqual(result["verdict"], "FAIL")

    @unittest.skipUnless(FFMPEG, "ffmpeg not available")
    def test_truncated_real_copy_is_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            whole = Path(tmp) / "whole.mp4"
            make_synthetic(whole)
            truncated = Path(tmp) / "truncated.mp4"
            truncated.write_bytes(whole.read_bytes()[: whole.stat().st_size // 3])
            result = self.result_for(truncated)
        self.assertEqual(result["verdict"], "FAIL")

    @unittest.skipUnless(FFMPEG, "ffmpeg not available")
    def test_synthetic_vertical_with_audio_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "good.mp4"
            make_synthetic(media)
            result = self.result_for(media)
        self.assertEqual(result["verdict"], "PASS")
        self.assertTrue(all(c["pass"] for c in result["checks"]))
        self.assertEqual(result["professional_status"], "NOT_EVALUATED")
        self.assertEqual(result["business_status"], "NOT_EVALUATED")

    @unittest.skipUnless(FFMPEG, "ffmpeg not available")
    def test_silent_fails_when_audio_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "silent.mp4"
            make_synthetic(media, audio=False)
            criteria = json.loads(json.dumps(CRITERIA))
            criteria["e1_technical_minimum"]["audio_policy"] = "REQUIRED"
            result = verify_export.verify_media(media, criteria, CRITERIA_SHA, "test-criteria")
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(any(c["id"] == "audio_policy" and not c["pass"]
                            for c in result["checks"]))

    @unittest.skipUnless(FFMPEG, "ffmpeg not available")
    def test_square_fails_vertical_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "square.mp4"
            make_synthetic(media, width=720, height=720)
            result = self.result_for(media)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(any(c["id"] == "vertical_format" and not c["pass"]
                            for c in result["checks"]))

    def test_criteria_without_minimums_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{}", encoding="utf8")
            with self.assertRaises(ValueError):
                verify_export.load_criteria(bad)


if __name__ == "__main__":
    unittest.main()

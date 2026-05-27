#!/usr/bin/env python3
"""Validate the static audio demo page for anonymous review."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")

    for forbidden in [
        "/home/",
        "home/tione",
        "tione/notebook",
        "Anonymous Authors,",
    ]:
        if forbidden in html:
            fail(f"found forbidden reviewer-visible string: {forbidden}")

    if html.count('class="source-demo-card"') != 14:
        fail("expected 14 benchmark source demo cards")

    if html.count('class="comparison-demo-card"') != 4:
        fail("expected 4 baseline comparison demo cards")

    if re.search(r"<(?:th|b)>Style(?::)?</(?:th|b)>", html) or re.search(
        r"<(?:th|b)>Event(?::)?</(?:th|b)>", html
    ):
        fail("demo should use Scenario Style and NV terminology")

    for required in [
        "Scenario Style",
        "text_with_NV",
        "transcription_with_NV",
        "translation_with_NV",
        "Emotion Score",
        "Scenario Style Score",
    ]:
        if required not in html:
            fail(f"missing required label: {required}")

    if html.count("<details") < 20:
        fail("expected long captions/reasons to be folded with details")

    if "<td></td>" in html or "<p></p>" in html:
        fail("found empty demo cell or folded reason")

    audio_srcs = re.findall(r'<source src="([^"]+)" type="audio/wav">', html)
    if len(audio_srcs) < 30:
        fail("expected at least 30 audio source tags")

    for src in audio_srcs:
        if src.startswith("/") or src.startswith("http"):
            fail(f"audio path is not local relative static asset: {src}")
        audio_path = ROOT / src
        if not audio_path.exists():
            fail(f"missing audio asset: {src}")
        if audio_path.stat().st_size == 0:
            fail(f"empty audio asset: {src}")

    print(
        f"OK: {len(audio_srcs)} audio assets, 14 source cards, "
        "4 comparison cards, anonymous static paths"
    )


if __name__ == "__main__":
    main()

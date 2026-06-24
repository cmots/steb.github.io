#!/usr/bin/env python3
"""Build the anonymous static audio demo section from local benchmark artifacts."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
STATIC_AUDIO = ROOT / "static" / "audio"

SOURCE_SAMPLES = {
    ("normal", "zh"): [
        "ytdp_0008_10314862_S00020",
        "ytdp_0008_11046006_S00054",
        "ytdp_0008_135337875_S00011",
        "ytdp_0008_178130903_S00057",
    ],
    ("normal", "en"): [
        "ytdp_0008_10251880_S00020",
        "ytdp_0008_10254889_S00045",
        "ytdp_0008_10254891_S00041",
        "ytdp_0008_10254886_S00064",
    ],
    ("event", "zh"): [
        "ytdp_0001_2010_0001_zh_fj9rajyzwzjohi5_e0021wnwimt_S000300_spk1",
        "ytdp_0008_761264393_001_S00013",
        "ytdp_0001_2018_0001_zh_mzc0020020tlz7s_m0045qjjsk5_S000219_spk0",
    ],
    ("event", "en"): [
        "ytdp_0001_2016_0001_zh_mzc00200azq68gu_k4100g2ce8k_S000057_spk4",
        "ytdp_0001_2015_0001_zh_fcq46oukym4tmso_s0019k5t9s5_S000045_spk0",
        "ytdp_0001_2018_0001_zh_d5w79ke56k4n2ba_z0029s2azuh_S000142_spk0",
    ],
}

COMPARISON_SAMPLES = [
    ("normal", "zh", "ytdp_0008_10314862_S00020"),
    ("normal", "en", "ytdp_0008_10251880_S00020"),
    ("event", "zh", "ytdp_0001_2010_0001_zh_fj9rajyzwzjohi5_e0021wnwimt_S000300_spk1"),
    ("event", "en", "ytdp_0001_2016_0001_zh_mzc00200azq68gu_k4100g2ce8k_S000057_spk4"),
]

@dataclass(frozen=True)
class BaselineSpec:
    key: str
    label: str
    records_dir: Path
    score_dir: Path
    wav_search_dir: Path
    annotation_dir: Path | None = None
    style_dir: Path | None = None


def env_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set {name} before running this script.")
    return Path(value).expanduser().resolve()


def load_jsonl_by_id(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def first_jsonl(directory: Path, prefix: str) -> Path:
    matches = sorted(directory.glob(prefix))
    if not matches:
        raise FileNotFoundError(f"No JSONL matching {prefix} in {directory}")
    return matches[0]


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def e(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def details(summary: str, body: object, class_name: str = "demo-details") -> str:
    text = e(body).replace("\n", "<br>")
    return f'<details class="{class_name}"><summary>{e(summary)}</summary><p>{text}</p></details>'


def audio_tag(src: str) -> str:
    return f'<audio controls preload="none"><source src="{e(src)}" type="audio/wav"></audio>'


def copy_audio(source: Path, category: str, name: str) -> str:
    if not source.exists():
        raise FileNotFoundError(source)
    target_dir = STATIC_AUDIO / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name(name)
    shutil.copy2(source, target)
    return target.relative_to(ROOT).as_posix()


def resolve_baseline_wav(record: dict, search_dir: Path) -> Path:
    raw = record.get("hyp_wav_path")
    if raw:
        raw_path = Path(raw)
        if raw_path.exists():
            return raw_path
        filename = raw_path.name
        for found in search_dir.rglob(filename):
            if found.is_file():
                return found
    raise FileNotFoundError(f"Missing baseline wav for {record.get('id')} under {search_dir}")


def baseline_specs(
    benchmark_root: Path,
    baselines_root: Path,
    pool: str,
    lang: str,
) -> list[BaselineSpec]:
    direction = "zh2en" if lang == "zh" else "en2zh"
    checkpoint_root = benchmark_root / "vllm_experiments_20260408_checkpoint227" / lang
    seed_root = benchmark_root / "doubao-ast" / lang

    return [
        BaselineSpec(
            key="two_vox",
            label="Cascaded System",
            records_dir=baselines_root / f"two_vox_{direction}" / pool / "full_eval_allmetrics_20260519",
            score_dir=baselines_root / f"two_vox_{direction}" / pool / "full_eval_allmetrics_20260519",
            wav_search_dir=baselines_root / f"two_vox_{direction}" / pool,
        ),
        BaselineSpec(
            key="uniss",
            label="UniSS",
            records_dir=checkpoint_root / "uniss_quality" / "eval" / pool,
            score_dir=checkpoint_root / "uniss_quality" / "eval_jsonl_20260515_clean" / pool,
            wav_search_dir=checkpoint_root / "uniss_quality",
            annotation_dir=checkpoint_root / "uniss_quality" / "eval" / pool,
            style_dir=checkpoint_root
            / "uniss_quality"
            / "eval_jsonl_20260515_clean"
            / pool
            / "style_v4_12_3_run3_20260518",
        ),
        BaselineSpec(
            key="seamless",
            label="SeamlessExpressive",
            records_dir=baselines_root / f"seamless_{direction}" / pool / "full_eval_allmetrics",
            score_dir=baselines_root / f"seamless_{direction}" / pool / "full_eval_clean_20260515",
            wav_search_dir=baselines_root / f"seamless_{direction}" / pool,
            annotation_dir=baselines_root / f"seamless_{direction}" / pool / "full_eval_clean_20260515",
            style_dir=baselines_root
            / f"seamless_{direction}"
            / pool
            / "style_v4_12_3_run3_20260518",
        ),
        BaselineSpec(
            key="seed_live",
            label="Seed Live",
            records_dir=seed_root / "full_eval_allmetrics_20260519" / pool,
            score_dir=seed_root / "full_eval_allmetrics_20260519" / pool,
            wav_search_dir=seed_root,
        ),
        BaselineSpec(
            key="step_audio",
            label="Step-Audio 2",
            records_dir=checkpoint_root / "orig_normal" / "eval" / pool,
            score_dir=checkpoint_root / "orig_normal" / "eval_jsonl_20260515_clean" / pool,
            wav_search_dir=checkpoint_root / "orig_normal",
            annotation_dir=checkpoint_root / "orig_normal" / "eval" / pool,
            style_dir=checkpoint_root
            / "orig_normal"
            / "eval_jsonl_20260515_clean"
            / pool
            / "style_v4_12_3_run3_20260518",
        ),
    ]


def load_baseline_bundle(spec: BaselineSpec, pool: str) -> dict:
    records = load_jsonl_by_id(spec.records_dir / "eval_records_merged.jsonl")
    annotation_records = records
    if spec.annotation_dir and (spec.annotation_dir / "eval_records_merged.jsonl").exists():
        annotation_records = load_jsonl_by_id(spec.annotation_dir / "eval_records_merged.jsonl")
    scores = load_jsonl_by_id(first_jsonl(spec.score_dir, "eval_results*.jsonl"))
    style_scores: dict[str, dict] = {}
    if pool == "normal" and spec.style_dir and spec.style_dir.exists():
        style_scores = load_jsonl_by_id(first_jsonl(spec.style_dir, "eval_results*.jsonl"))
    return {
        "spec": spec,
        "records": records,
        "annotation_records": annotation_records,
        "scores": scores,
        "style_scores": style_scores,
    }


def source_audio_path(benchmark_root: Path, lang: str, row: dict) -> Path:
    return benchmark_root / lang / row["wav_path"]


def source_translation(row: dict, lang: str) -> str:
    translation = row.get("translation")
    if isinstance(translation, dict):
        target_lang = "en" if lang == "zh" else "zh"
        return translation.get(target_lang) or ""
    return translation or ""


def render_source_card(benchmark_root: Path, pool: str, lang: str, row: dict, index: int) -> str:
    asset_pool = "nv" if pool == "event" else pool
    wav = copy_audio(
        source_audio_path(benchmark_root, lang, row),
        f"benchmark/{asset_pool}/{lang}",
        f"{row['id']}.wav",
    )
    pool_label = "NV" if pool == "event" else pool.title()
    heading = f"{pool_label} {lang.upper()} #{index}"
    if pool == "normal":
        return f"""
                <article class="source-demo-card">
                    <h4>{e(heading)}</h4>
                    <table class="demo-table source-table">
                        <tbody>
                            <tr><th>Source Audio</th><td>{audio_tag(wav)}</td></tr>
                            <tr><th>Transcription</th><td class="transcript">{e(row.get("text"))}</td></tr>
                            <tr><th>Translation</th><td class="transcript">{e(source_translation(row, lang))}</td></tr>
                            <tr><th>Emotion</th><td>{e(row.get("emotion"))}</td></tr>
                            <tr><th>Scenario Style</th><td>{e(row.get("style"))}</td></tr>
                            <tr><th>Caption</th><td>{details("Show caption", row.get("caption"))}</td></tr>
                        </tbody>
                    </table>
                </article>"""

    return f"""
                <article class="source-demo-card">
                    <h4>{e(heading)}</h4>
                    <table class="demo-table source-table">
                        <tbody>
                            <tr><th>Source Audio</th><td>{audio_tag(wav)}</td></tr>
                            <tr><th>Transcription</th><td class="transcript">{e(row.get("text"))}</td></tr>
                            <tr><th>Translation</th><td class="transcript">{e(source_translation(row, lang))}</td></tr>
                            <tr><th>text_with_NV</th><td class="transcript">{e(row.get("text_with_events"))}</td></tr>
                        </tbody>
                    </table>
                </article>"""


def render_source_section(benchmark_root: Path) -> str:
    pieces: list[str] = []
    for pool in ["normal", "event"]:
        for lang in ["zh", "en"]:
            file_name = "normal_clean.jsonl" if pool == "normal" else "event_clean.jsonl"
            rows = load_jsonl_by_id(benchmark_root / lang / file_name)
            cards = "\n".join(
                render_source_card(benchmark_root, pool, lang, rows[sample_id], i + 1)
                for i, sample_id in enumerate(SOURCE_SAMPLES[(pool, lang)])
            )
            pool_label = "NV" if pool == "event" else pool.title()
            pieces.append(
                f"""
            <div class="demo-subsection">
                <h3>{e(pool_label)} Source Samples: {e(lang.upper())}</h3>
                <div class="source-demo-grid">
{cards}
                </div>
            </div>"""
            )
    return "\n".join(pieces)


def speech_text(record: dict, pool: str) -> str:
    if pool == "event":
        return (
            record.get("hyp_asr_text_with_event")
            or record.get("hyp_text_with_events")
            or record.get("hyp_asr_text")
            or ""
        )
    return record.get("hyp_asr_text") or ""


def render_normal_comparison(
    benchmark_root: Path,
    lang: str,
    row: dict,
    bundles: list[dict],
) -> str:
    src_wav = copy_audio(
        source_audio_path(benchmark_root, lang, row),
        f"comparison/normal/{lang}",
        f"source_{row['id']}.wav",
    )
    rows_html = []
    for bundle in bundles:
        spec = bundle["spec"]
        record = bundle["records"][row["id"]]
        annotation_record = bundle["annotation_records"].get(row["id"], record)
        score = bundle["scores"].get(row["id"], {})
        style_score = bundle["style_scores"].get(row["id"], {})
        wav = copy_audio(
            resolve_baseline_wav(record, spec.wav_search_dir),
            f"comparison/normal/{lang}",
            f"{spec.key}_{row['id']}.wav",
        )
        rows_html.append(
            f"""
                            <tr>
                                <td>{e(spec.label)}</td>
                                <td>{audio_tag(wav)}</td>
                                <td class="transcript">{e(speech_text(record, "normal"))}</td>
                                <td>{e(annotation_record.get("hyp_emotion") or annotation_record.get("hyp_emotion_text"))}</td>
                                <td>{e(score.get("emotion_score"))}</td>
                                <td>{details("Reason", score.get("emotion_reason"), "demo-details reason-details")}</td>
                                <td>{e(annotation_record.get("hyp_style") or annotation_record.get("hyp_style_text"))}</td>
                                <td>{e(style_score.get("style_score", score.get("style_score")))}</td>
                                <td>{details("Reason", style_score.get("style_reason", score.get("style_reason")), "demo-details reason-details")}</td>
                            </tr>"""
        )
    return f"""
            <article class="comparison-demo-card">
                <h3>Baseline Comparison: Normal {e(lang.upper())}</h3>
                <div class="source-context">
                    <div>{audio_tag(src_wav)}</div>
                    <p><b>Source Transcription:</b> {e(row.get("text"))}</p>
                    <p><b>Source Emotion:</b> {e(row.get("emotion"))}</p>
                    <p><b>Source Scenario Style:</b> {e(row.get("style"))}</p>
                </div>
                <div class="demo-table-wrap">
                    <table class="demo-table comparison-table normal-comparison-table">
                        <thead>
                            <tr>
                                <th>Baseline</th>
                                <th>Target Audio</th>
                                <th>Target Translation</th>
                                <th>Target Emotion</th>
                                <th>Emotion Score</th>
                                <th>Emotion Reason</th>
                                <th>Target Scenario Style</th>
                                <th>Scenario Style Score</th>
                                <th>Scenario Style Reason</th>
                            </tr>
                        </thead>
                        <tbody>
{''.join(rows_html)}
                        </tbody>
                    </table>
                </div>
            </article>"""


def render_event_comparison(
    benchmark_root: Path,
    lang: str,
    row: dict,
    bundles: list[dict],
) -> str:
    src_wav = copy_audio(
        source_audio_path(benchmark_root, lang, row),
        f"comparison/nv/{lang}",
        f"source_{row['id']}.wav",
    )
    rows_html = []
    for bundle in bundles:
        spec = bundle["spec"]
        record = bundle["records"][row["id"]]
        score = bundle["scores"].get(row["id"], {})
        wav = copy_audio(
            resolve_baseline_wav(record, spec.wav_search_dir),
            f"comparison/nv/{lang}",
            f"{spec.key}_{row['id']}.wav",
        )
        rows_html.append(
            f"""
                            <tr>
                                <td>{e(spec.label)}</td>
                                <td>{audio_tag(wav)}</td>
                                <td class="transcript">{e(speech_text(record, "event"))}</td>
                                <td>{e(score.get("event_score"))}</td>
                                <td>{details("Reason", score.get("event_reason"), "demo-details reason-details")}</td>
                            </tr>"""
        )
    return f"""
            <article class="comparison-demo-card">
                <h3>Baseline Comparison: NV {e(lang.upper())}</h3>
                <div class="source-context">
                    <div>{audio_tag(src_wav)}</div>
                    <p><b>Source transcription_with_NV:</b> {e(row.get("text_with_events"))}</p>
                </div>
                <div class="demo-table-wrap">
                    <table class="demo-table comparison-table">
                        <thead>
                            <tr>
                                <th>Baseline</th>
                                <th>Target Audio</th>
                                <th>Target translation_with_NV</th>
                                <th>NV Score</th>
                                <th>NV Reason</th>
                            </tr>
                        </thead>
                        <tbody>
{''.join(rows_html)}
                        </tbody>
                    </table>
                </div>
            </article>"""


def render_comparison_section(benchmark_root: Path, baselines_root: Path) -> str:
    pieces: list[str] = []
    for pool, lang, sample_id in COMPARISON_SAMPLES:
        file_name = "normal_clean.jsonl" if pool == "normal" else "event_clean.jsonl"
        row = load_jsonl_by_id(benchmark_root / lang / file_name)[sample_id]
        bundles = [
            load_baseline_bundle(spec, pool)
            for spec in baseline_specs(benchmark_root, baselines_root, pool, lang)
        ]
        if pool == "normal":
            pieces.append(render_normal_comparison(benchmark_root, lang, row, bundles))
        else:
            pieces.append(render_event_comparison(benchmark_root, lang, row, bundles))
    return "\n".join(pieces)


def replace_audio_section(section_html: str) -> None:
    html_text = INDEX.read_text(encoding="utf-8")
    pattern = re.compile(
        r"<!-- AUDIO_DEMO_BEGIN -->.*?<!-- AUDIO_DEMO_END -->",
        flags=re.DOTALL,
    )
    replacement = f"<!-- AUDIO_DEMO_BEGIN -->\n{section_html}\n            <!-- AUDIO_DEMO_END -->"
    new_html, count = pattern.subn(replacement, html_text)
    if count != 1:
        raise SystemExit("Could not replace audio demo section exactly once.")
    INDEX.write_text(new_html, encoding="utf-8")


def main() -> None:
    benchmark_root = env_path("STEB_BENCHMARK_ROOT")
    baselines_root = env_path("STEB_BASELINES_ROOT")
    if STATIC_AUDIO.exists():
        shutil.rmtree(STATIC_AUDIO)
    section = f"""
            <div class="demo-block">
                <h3>Benchmark Source Audio</h3>
                <p class="demo-description">Source samples from the benchmark with human-readable expressive annotations.</p>
{render_source_section(benchmark_root)}
            </div>

            <div class="demo-block">
                <h3>Baseline Output Comparisons</h3>
                <p class="demo-description">For each source audio, target translations are transcribed from generated speech outputs; long judge rationales are folded by default.</p>
{render_comparison_section(benchmark_root, baselines_root)}
            </div>"""
    replace_audio_section(section)


if __name__ == "__main__":
    main()

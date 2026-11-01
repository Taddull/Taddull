"""Human-readable verification reports (Markdown)."""

from __future__ import annotations

import math


def _f(x, unit=""):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        if math.isinf(x):
            return "∞" + unit
        if math.isnan(x):
            return "n/a"
        return f"{x:.2f}{unit}"
    return f"{x}{unit}"


def write_markdown_report(rep: dict, path: str) -> None:
    lines = []
    status = rep.get("status", "unknown").upper()
    lines.append(f"# Smart Revision Exporter - verification report\n")
    lines.append(f"**Result: {status}**  ")
    if rep.get("mode"):
        lines.append(f"Mode: {rep['mode']} (verification level: {rep.get('level')})  ")
    if rep.get("output"):
        lines.append(f"Output: `{rep['output'].get('path')}`  ")
        lines.append(f"Output SHA-256: `{rep['output'].get('sha256')}`  ")
    if rep.get("master_fingerprint"):
        lines.append(f"Master SHA-256: `{rep['master_fingerprint']}`  ")
    lines.append(f"Engine version: {rep.get('engine_version')}\n")
    v = rep.get("video") or {}
    if v:
        lines.append("## Video\n")
        lines.append("| Metric | Value |\n|---|---|")
        rows = [
            ("Master frames", v.get("master_frames")),
            ("Output frames", v.get("output_frames")),
            ("Unchanged frames compared", v.get("compared_unchanged")),
            ("Unchanged frames pixel-identical", v.get("identical_unchanged")),
            ("Unchanged frames not decoded (fast mode)", v.get("unverified_unchanged")),
            ("Re-encoded frames", v.get("reencoded_frames")),
            ("  of which boundary frames (unchanged content)", v.get("boundary_frames")),
            ("Encode fidelity, luma PSNR min/mean (dB)",
             f"{_f(v.get('encode_fidelity_psnr_y', {}).get('min'))} / {_f(v.get('encode_fidelity_psnr_y', {}).get('mean'))}"),
            ("Boundary render vs master, luma PSNR min (dB)",
             _f(v.get("boundary_render_vs_master_psnr_y", {}).get("min"))),
            ("Guard render vs master, luma PSNR min (dB)", _f(v.get("guard_render_vs_master_psnr_y", {}).get("min"))),
        ]
        for k, val in rows:
            if val is not None:
                lines.append(f"| {k} | {val} |")
        lines.append("")
        segs = v.get("segments") or []
        if segs:
            lines.append("### Segments\n")
            lines.append("| Kind | Master frames | Output frames | Revised (output) | Boundary |\n|---|---|---|---|---|")
            for s in segs:
                lines.append(f"| {s['kind']} | {s['master'][0]}-{s['master'][1] - 1} | {s['output'][0]}-{s['output'][1] - 1} "
                             f"| {s.get('revised') or ''} | {s.get('boundary_frames', 0)} |")
            lines.append("")
    if rep.get("audio"):
        lines.append("## Audio\n")
        for a in rep["audio"]:
            lines.append(f"- Track {a.get('index')}: **{a.get('strategy')}** - {a.get('reason')}")
        lines.append("")
    lines.append("## Checks\n")
    lines.append("| Check | Status | Detail |\n|---|---|---|")
    for c in rep.get("checks", []):
        detail = str(c.get("detail", "")).replace("|", "\\|")
        lines.append(f"| {c.get('name')} | {c.get('status', '').upper()} | {detail} |")
    lines.append("")
    enc = rep.get("encoding") or {}
    if enc.get("x264_params"):
        lines.append("## Encoding\n")
        lines.append(f"- Patch encoder: libx264, preset {enc['video'].get('preset')}, "
                     f"{'CRF ' + str(enc['video'].get('crf')) if enc['video'].get('crf') is not None else 'two-pass ' + str(enc['video'].get('bitrate_kbps')) + ' kbit/s'}")
        lines.append(f"- x264 parameters: `{enc['x264_params']}`")
        lines.append(f"- Output parameter sets: {enc.get('parameter_sets')}")
        lines.append(f"- Audio encoder: {enc.get('audio_encoder') or 'not used (audio copied)'}")
        lines.append("")
    if rep.get("tradeoffs"):
        lines.append("## Revision-ready structure\n")
        for k, val in rep["tradeoffs"].items():
            lines.append(f"- {k.replace('_', ' ')}: {val}")
        lines.append("")
    t = rep.get("timings_s")
    if t:
        lines.append("## Processing cost\n")
        for k, val in t.items():
            lines.append(f"- {k}: {val} s")
        costs = rep.get("costs") or {}
        if costs:
            lines.append(f"- frames decoded for verification: {costs.get('frames_decoded')} "
                         f"({costs.get('master_decode')})")
        lines.append("")
    if rep.get("failures"):
        lines.append("## Failures\n")
        for f in rep["failures"]:
            lines.append(f"- {f}")
    if rep.get("warnings"):
        lines.append("## Warnings\n")
        for w in rep["warnings"]:
            lines.append(f"- {w}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

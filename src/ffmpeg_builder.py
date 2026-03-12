import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List

from config.settings import AUDIO_BITRATE, FFMPEG_CRF, FFMPEG_PRESET


def _run(cmd: List[str]) -> None:
    print(f"[CMD] {' '.join(cmd[:6])}... ({len(cmd)} args)")
    subprocess.run(cmd, check=True)


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def _prepare_clip(
    src: Path,
    dst: Path,
    width: int,
    height: int,
    duration: int,
    fps: int,
) -> None:
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps}"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-t",
            str(duration),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            FFMPEG_PRESET,
            "-crf",
            FFMPEG_CRF,
            str(dst),
        ]
    )


def _safe_drawtext_text(raw: str) -> str:
    # Keep only drawtext-safe characters to avoid filter parser errors in CI.
    text = raw.replace("\\", " ")
    text = text.replace("\n", " ")
    text = text.replace(":", " - ").replace(";", " ").replace(",", " ")
    text = text.replace("'", "").replace('"', "")
    text = re.sub(r"[^A-Za-z0-9 .,!?\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "STAY HARD"


def _fmt_ass_time(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _group_words_into_lines(
    word_events: list[dict],
    max_words_per_line: int = 5,
    max_gap_s: float = 0.6,
) -> list[dict]:
    """Group word-boundary events into subtitle lines."""
    if not word_events:
        return []

    lines: list[dict] = []
    buf_words: list[str] = []
    buf_start = 0.0
    buf_end = 0.0
    buf_kara: list[dict] = []

    for ev in word_events:
        word = ev["text"]
        start = ev["offset"]
        dur = ev["duration"]
        end = start + dur

        # Start new line if too many words or big pause.
        if buf_words and (len(buf_words) >= max_words_per_line or (start - buf_end) > max_gap_s):
            lines.append({
                "start": buf_start,
                "end": buf_end,
                "text": " ".join(buf_words),
                "words": list(buf_kara),
            })
            buf_words = []
            buf_kara = []

        if not buf_words:
            buf_start = start

        buf_words.append(word)
        buf_kara.append({"text": word, "offset": start, "duration": dur})
        buf_end = end

    if buf_words:
        lines.append({
            "start": buf_start,
            "end": buf_end,
            "text": " ".join(buf_words),
            "words": list(buf_kara),
        })

    return lines


def _write_synced_ass(
    word_events: list[dict],
    ass_path: Path,
    width: int,
    height: int,
) -> Path:
    """Write ASS subtitles synced to actual word timestamps from edge-tts.

    Style: large bold white text, thick black outline, center screen.
    Karaoke highlight: words turn bright yellow as spoken (viral motivation style).
    """
    is_short = height > width
    # Large, impactful text — like top motivation/quotes channels.
    font_size = 64 if is_short else 48
    # Place text in lower-center area but above bottom UI on phones.
    margin_v = 350 if is_short else 100
    # ASS karaoke: \k fills SecondaryColour → PrimaryColour.
    # PrimaryColour = what word becomes AFTER its time (spoken/highlighted).
    # SecondaryColour = what word looks like BEFORE its time (upcoming).
    primary_color = "&H0000D4FF"    # Bright yellow-orange (spoken word — karaoke fills with this)
    secondary_color = "&H00FFFFFF"  # White (upcoming words — shown before karaoke timer)
    outline_color = "&H00000000"    # Black outline
    shadow_color = "&H80000000"     # Semi-transparent black shadow

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Kara,DejaVu Sans,{font_size},{primary_color},{secondary_color},{outline_color},{shadow_color},"
        "1,0,0,0,100,100,1,0,1,4,2,2,30,30,"
        f"{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lines = _group_words_into_lines(word_events, max_words_per_line=4 if is_short else 6)
    events: list[str] = []
    for line in lines:
        line_start = line["start"]
        line_end = line["end"] + 0.15  # Small buffer so last word stays visible.
        # Build karaoke tags from per-word timing.
        parts = []
        for w in line["words"]:
            dur_cs = max(5, int(w["duration"] * 100))
            safe_text = _safe_drawtext_text(w["text"]).upper()
            parts.append(f"{{\\kf{dur_cs}}}{safe_text}")
        kara_text = " ".join(parts)
        events.append(
            f"Dialogue: 0,{_fmt_ass_time(line_start)},{_fmt_ass_time(line_end)},Kara,,0,0,0,,{kara_text}"
        )

    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    print(f"[SUBS] ASS written: {len(events)} dialogue lines, {len(word_events)} word events → {ass_path}")
    return ass_path


def assemble_video(
    clips: List[Path],
    scenes: List[Dict[str, str | int]],
    voiceover_path: Path,
    word_events: list[dict],
    music_path: Path | None,
    output_path: Path,
    temp_dir: Path,
    width: int,
    height: int,
    fps: int,
) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)

    prepared: List[Path] = []
    for i, clip in enumerate(clips):
        dst = temp_dir / f"prep_{i:02d}.mp4"
        _prepare_clip(
            src=clip,
            dst=dst,
            width=width,
            height=height,
            duration=int(scenes[i]["duration"]),
            fps=fps,
        )
        prepared.append(dst)

    concat_file = temp_dir / "concat.txt"
    concat_file.write_text("\n".join([f"file '{p.resolve().as_posix()}'" for p in prepared]), encoding="utf-8")
    silent_video = temp_dir / "video_no_audio.mp4"

    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(silent_video),
        ]
    )

    voice_dur = _probe_duration(voiceover_path)
    clip_dur = _probe_duration(silent_video)
    # Voice is the master clock — video duration = voice + small outro buffer.
    final_duration = voice_dur + 1.5

    # If video is shorter than voice, loop it so voice never gets cut off.
    loop_video = clip_dur < voice_dur
    if loop_video:
        looped = temp_dir / "video_looped.mp4"
        _run(
            [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(silent_video),
                "-t", f"{final_duration:.2f}",
                "-c", "copy",
                str(looped),
            ]
        )
        silent_video = looped

    ass_path = _write_synced_ass(word_events=word_events, ass_path=temp_dir / "captions.ass", width=width, height=height)

    # === PASS 1: burn subtitles + color grading into the silent video ===
    # This avoids filter_complex path-escaping issues with the subtitles filter.
    graded_video = temp_dir / "video_graded.mp4"
    # For -vf subtitles filter: escape only special chars that ffmpeg filter parser uses.
    # On Linux CI the path has no colons or backslashes, so minimal escaping needed.
    ass_posix = ass_path.resolve().as_posix()
    # Escape chars: \ → \\, : → \:, ' → \', [ → \[, ] → \]
    ass_escaped = (
        ass_posix
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
    vf_burn = (
        f"eq=contrast=1.1:brightness=-0.03:saturation=0.85,"
        f"subtitles={ass_escaped}"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(silent_video),
            "-vf", vf_burn,
            "-t", f"{final_duration:.2f}",
            "-c:v", "libx264",
            "-preset", FFMPEG_PRESET,
            "-crf", FFMPEG_CRF,
            "-an",
            str(graded_video),
        ]
    )
    print(f"[VIDEO] voice={voice_dur:.1f}s clips={clip_dur:.1f}s final={final_duration:.2f}s loop={loop_video}")

    # === PASS 2: combine graded video + voice + optional music ===
    cmd = [
        "ffmpeg", "-y",
        "-i", str(graded_video),
        "-i", str(voiceover_path),
    ]

    # Pad voice audio with silence to fill the full video duration.
    voice_pad = f"apad=whole_dur={final_duration:.2f}"

    if music_path and music_path.exists():
        cmd.extend(["-stream_loop", "-1", "-i", str(music_path)])
        cmd.extend(
            [
                "-filter_complex",
                (
                    f"[1:a]acompressor=threshold=-18dB:ratio=2.5:attack=5:release=120,{voice_pad}[va];"
                    "[2:a]highpass=f=80,lowpass=f=14000,volume=0.16[ma];"
                    "[ma][va]sidechaincompress=threshold=0.03:ratio=10:attack=15:release=250[ducked];"
                    "[va][ducked]amix=inputs=2:duration=first:normalize=0[a]"
                ),
                "-map", "0:v",
                "-map", "[a]",
            ]
        )
    else:
        # Fallback audio bed so videos are not dry when no music file is provided.
        cmd.extend(["-f", "lavfi", "-t", f"{final_duration:.2f}", "-i", "anoisesrc=color=pink:amplitude=0.015"])
        cmd.extend(
            [
                "-filter_complex",
                (
                    f"[1:a]acompressor=threshold=-18dB:ratio=2.5:attack=5:release=120,{voice_pad}[va];"
                    "[2:a]lowpass=f=1800,highpass=f=90,volume=0.07[ba];"
                    "[va][ba]amix=inputs=2:duration=first:normalize=0[a]"
                ),
                "-map", "0:v",
                "-map", "[a]",
            ]
        )

    cmd.extend(
        [
            "-t",
            f"{final_duration:.2f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            str(output_path),
        ]
    )
    # Log the full final command for debugging subtitle/audio issues.
    print(f"[FFMPEG FINAL] {' '.join(cmd)}")
    _run(cmd)

    meta_path = output_path.with_suffix(".json")
    meta_path.write_text(
        json.dumps({"duration_seconds": final_duration, "scenes": len(scenes)}, indent=2),
        encoding="utf-8",
    )
    return output_path

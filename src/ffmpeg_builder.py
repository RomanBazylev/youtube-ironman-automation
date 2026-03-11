import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List

from config.settings import AUDIO_BITRATE, FFMPEG_CRF, FFMPEG_PRESET


def _run(cmd: List[str]) -> None:
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
            "24",
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


def _to_karaoke_text(caption: str, duration_s: float) -> str:
    words = [w for w in caption.split() if w]
    if not words:
        words = ["STAY", "HARD"]

    total_cs = max(30, int(duration_s * 100))
    base = max(8, total_cs // len(words))
    rem = total_cs - base * len(words)

    parts = []
    for i, w in enumerate(words):
        extra = 1 if i < rem else 0
        parts.append(f"{{\\k{base + extra}}}{w}")
    return " ".join(parts)


def _write_karaoke_ass(
    scenes: List[Dict[str, str | int]],
    ass_path: Path,
    width: int,
    height: int,
) -> Path:
    is_short = height > width
    font_size = 54 if is_short else 42
    margin_v = 210 if is_short else 80

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Kara,DejaVu Sans,{font_size},&H00FFFFFF,&H0000A5FF,&H00000000,&H4D000000,"
        "1,0,0,0,100,100,0,0,1,3,0,2,40,40,"
        f"{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events: List[str] = []
    start = 0.0
    for scene in scenes:
        dur = float(scene["duration"])
        end = start + dur
        txt = _safe_drawtext_text(str(scene["caption_text"]))
        kara = _to_karaoke_text(txt, dur)
        events.append(
            f"Dialogue: 0,{_fmt_ass_time(start)},{_fmt_ass_time(end)},Kara,,0,0,0,,{kara}"
        )
        start = end

    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return ass_path


def assemble_video(
    clips: List[Path],
    scenes: List[Dict[str, str | int]],
    voiceover_path: Path,
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
    final_duration = min(max(clip_dur, voice_dur), 185.0)

    ass_path = _write_karaoke_ass(scenes=scenes, ass_path=temp_dir / "captions.ass", width=width, height=height)
    ass_filter_path = ass_path.resolve().as_posix().replace(":", "\\:")
    vf = f"subtitles='{ass_filter_path}'"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(voiceover_path),
    ]

    if music_path and music_path.exists():
        cmd.extend(["-stream_loop", "-1", "-i", str(music_path)])
        cmd.extend(
            [
                "-filter_complex",
                (
                    f"[0:v]{vf}[v];"
                    "[1:a]loudnorm=I=-16:LRA=11:TP=-1.5,acompressor=threshold=-18dB:ratio=2.5:attack=5:release=120[va];"
                    "[2:a]highpass=f=80,lowpass=f=14000,volume=0.16[ma];"
                    "[ma][va]sidechaincompress=threshold=0.03:ratio=10:attack=15:release=250[ducked];"
                    "[va][ducked]amix=inputs=2:duration=first:normalize=0[a]"
                ),
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        )
    else:
        # Fallback audio bed so videos are not dry when no music file is provided.
        cmd.extend(["-f", "lavfi", "-t", f"{final_duration:.2f}", "-i", "anoisesrc=color=pink:amplitude=0.015"])
        cmd.extend(
            [
                "-filter_complex",
                (
                    f"[0:v]{vf}[v];"
                    "[1:a]loudnorm=I=-16:LRA=11:TP=-1.5,acompressor=threshold=-18dB:ratio=2.5:attack=5:release=120[va];"
                    "[2:a]lowpass=f=1800,highpass=f=90,volume=0.07[ba];"
                    "[va][ba]amix=inputs=2:duration=first:normalize=0[a]"
                ),
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        )

    cmd.extend(
        [
            "-t",
            f"{final_duration:.2f}",
            "-c:v",
            "libx264",
            "-preset",
            FFMPEG_PRESET,
            "-crf",
            FFMPEG_CRF,
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            "-shortest",
            str(output_path),
        ]
    )
    _run(cmd)

    meta_path = output_path.with_suffix(".json")
    meta_path.write_text(
        json.dumps({"duration_seconds": final_duration, "scenes": len(scenes)}, indent=2),
        encoding="utf-8",
    )
    return output_path

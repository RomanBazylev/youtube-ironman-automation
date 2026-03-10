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

    is_short = height > width
    font_size = 54 if is_short else 38
    caption_y = "h*0.78" if is_short else "h*0.82"

    # Build caption drawtext chain with per-scene timing.
    draw_filters = []
    start = 0.0
    for scene in scenes:
        dur = float(scene["duration"])
        end = start + dur
        txt = _safe_drawtext_text(str(scene["caption_text"]))
        draw_filters.append(
            "drawtext="
            f"text='{txt}':"
            f"fontcolor=white:fontsize={font_size}:borderw=2:bordercolor=black:"
            "box=1:boxcolor=black@0.28:boxborderw=14:"
            "x=(w-text_w)/2:"
            f"y={caption_y}:"
            "fix_bounds=1:"
            f"enable='between(t,{start:.2f},{end:.2f})'"
        )
        start = end

    vf = ",".join(draw_filters) if draw_filters else "null"

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

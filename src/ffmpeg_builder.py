import json
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

    # Build caption drawtext chain with per-scene timing.
    draw_filters = []
    start = 0.0
    for scene in scenes:
        dur = float(scene["duration"])
        end = start + dur
        txt = str(scene["caption_text"]).replace("'", "\\'")
        draw_filters.append(
            "drawtext="
            f"text='{txt}':"
            "fontcolor=white:fontsize=56:borderw=2:bordercolor=black:"
            "x=(w-text_w)/2:y=h*0.78:"
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
                    "[1:a]volume=1.0[va];"
                    "[2:a]volume=0.18[ma];"
                    "[va][ma]amix=inputs=2:duration=first[a]"
                ),
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        )
    else:
        cmd.extend(
            [
                "-filter_complex",
                f"[0:v]{vf}[v]",
                "-map",
                "[v]",
                "-map",
                "1:a",
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

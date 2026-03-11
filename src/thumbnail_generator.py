import subprocess
from pathlib import Path


def _probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def generate_thumbnail(video_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dur = _probe_duration(video_path)
    # Pick a frame at ~25% of the video for a more interesting thumbnail.
    seek = min(1.5, dur * 0.25) if dur > 0.5 else 0
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            f"{seek:.3f}",
            "-vframes",
            "1",
            str(output_path),
        ],
        check=True,
    )
    return output_path

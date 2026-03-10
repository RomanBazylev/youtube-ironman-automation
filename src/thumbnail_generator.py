import subprocess
from pathlib import Path


def generate_thumbnail(video_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            "00:00:01.500",
            "-vframes",
            "1",
            str(output_path),
        ],
        check=True,
    )
    return output_path

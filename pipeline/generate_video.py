import argparse
import json
import random
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as file path (python pipeline/generate_video.py) in CI/local.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import (
    BUILD_DIR,
    MUSIC_DIR,
    OUTPUT_DIR,
    TEMP_DIR,
    THUMB_DIR,
    VIDEO_SPECS,
    ensure_build_dirs,
)
from src.caption_generator import generate_captions
from src.ffmpeg_builder import assemble_video
from src.idea_generator import generate_video_idea
from src.scene_generator import generate_scene_prompts
from src.script_generator import generate_script
from src.stock_fetcher import download_clips_for_scenes
from src.thumbnail_generator import generate_thumbnail
from src.voice_generator import generate_voiceover
from src.youtube_uploader import publish_video, set_thumbnail, upload_video


def _pick_music() -> Path | None:
    if not MUSIC_DIR.exists():
        return None
    files = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in {".mp3", ".wav", ".m4a"}]
    return random.choice(files) if files else None


def generate_single_video(force_type: str | None = None) -> dict:
    ensure_build_dirs()

    idea = generate_video_idea(force_type=force_type)
    script_pack = generate_script(idea)
    script_text = script_pack["script"]

    scenes = generate_scene_prompts(script=script_text, video_type=idea["video_type"])
    captions = generate_captions(scenes)
    for i, cap in enumerate(captions):
        scenes[i]["caption_text"] = cap

    clips = download_clips_for_scenes(
        scenes=scenes,
        output_dir=TEMP_DIR / "clips",
        video_type=idea["video_type"],
    )

    voiceover_path = TEMP_DIR / "voiceover.mp3"
    generate_voiceover(script_text, voiceover_path)

    spec = VIDEO_SPECS[idea["video_type"]]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_video = OUTPUT_DIR / f"{idea['video_type']}_{ts}.mp4"

    assemble_video(
        clips=clips,
        scenes=scenes,
        voiceover_path=voiceover_path,
        music_path=_pick_music(),
        output_path=output_video,
        temp_dir=TEMP_DIR / "render",
        width=spec.width,
        height=spec.height,
        fps=spec.fps,
    )

    thumb_path = THUMB_DIR / f"thumb_{ts}.jpg"
    generate_thumbnail(output_video, thumb_path)

    full_description = (
        f"{script_pack['seo_description']}\n\n"
        "#discipline #selfimprovement #stoicism #mindset #success"
    )
    video_id = upload_video(
        video_path=output_video,
        title=script_pack["seo_title"],
        description=full_description,
        tags=script_pack.get("tags", []),
        category_id="22",
        privacy_status="public",
    )
    set_thumbnail(video_id=video_id, thumbnail_path=thumb_path)
    publish_video(video_id)

    result = {
        "video_id": video_id,
        "video_type": idea["video_type"],
        "title": script_pack["seo_title"],
        "topic": idea["topic"],
        "output": str(output_video),
    }

    (BUILD_DIR / "last_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Clean transient files to reduce artifact size and CI runtime.
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    return result


def generate_multiple_videos(n: int, force_type: str | None = None) -> list[dict]:
    results = []
    for _ in range(max(1, n)):
        results.append(generate_single_video(force_type=force_type))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-type", choices=["short", "normal"], default=None)
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()

    results = generate_multiple_videos(n=args.count, force_type=args.video_type)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

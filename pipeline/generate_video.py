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
from src.youtube_uploader import get_recent_video_titles, publish_video, set_thumbnail, upload_video


def _pick_music() -> Path | None:
    if not MUSIC_DIR.exists():
        return None
    files = [p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in {".mp3", ".wav", ".m4a"}]
    return random.choice(files) if files else None


def _normalize_privacy_status(value: str) -> str:
    allowed = {"public", "private", "unlisted"}
    v = value.strip().lower()
    if v not in allowed:
        raise ValueError(f"Invalid privacy status: {value}. Allowed: public/private/unlisted")
    return v


def generate_single_video(force_type: str | None = None, privacy_status: str = "public") -> dict:
    ensure_build_dirs()

    resolved_video_type = force_type if force_type in {"short", "normal"} else random.choice(["short", "normal"])
    privacy_status = _normalize_privacy_status(privacy_status)

    try:
        try:
            recent_titles = get_recent_video_titles(limit=30)
        except Exception as e:
            print(f"[WARN] Could not fetch recent titles: {e}")
            recent_titles = []
        idea = generate_video_idea(
            force_type=resolved_video_type,
            recent_titles=recent_titles,
            candidates=3,
        )
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

        tag_list = script_pack.get("tags", ["discipline", "selfimprovement", "stoicism", "mindset"])
        hashtags = " ".join(f"#{t.strip().replace(' ', '')}" for t in tag_list[:8] if t.strip())
        if not hashtags:
            hashtags = "#discipline #selfimprovement #stoicism #mindset #success"
        full_description = f"{script_pack['seo_description']}\n\n{hashtags}"
        video_id = upload_video(
            video_path=output_video,
            title=script_pack["seo_title"],
            description=full_description,
            tags=script_pack.get("tags", []),
            category_id="22",
            privacy_status=privacy_status,
        )

        try:
            set_thumbnail(video_id=video_id, thumbnail_path=thumb_path)
        except Exception as e:
            print(f"[WARN] Thumbnail step failed, continuing: {e}")

        try:
            publish_video(video_id, privacy_status=privacy_status)
        except Exception as e:
            print(f"[WARN] Publish status update failed, continuing: {e}")

        result = {
            "video_id": video_id,
            "video_type": idea["video_type"],
            "privacy_status": privacy_status,
            "title": script_pack["seo_title"],
            "topic": idea["topic"],
            "output": str(output_video),
        }

        (BUILD_DIR / "last_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    finally:
        # Clean transient files to reduce artifact size and CI runtime.
        try:
            if TEMP_DIR.exists():
                shutil.rmtree(TEMP_DIR)
        except Exception as e:
            print(f"[WARN] Temp cleanup failed: {e}")


def generate_multiple_videos(
    n: int,
    force_type: str | None = None,
    privacy_status: str = "public",
) -> list[dict]:
    results = []
    for _ in range(max(1, n)):
        results.append(generate_single_video(force_type=force_type, privacy_status=privacy_status))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-type", choices=["auto", "short", "normal"], default="auto")
    parser.add_argument("--privacy-status", choices=["public", "private", "unlisted"], default="public")
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()

    forced = None if args.video_type == "auto" else args.video_type

    results = generate_multiple_videos(
        n=args.count,
        force_type=forced,
        privacy_status=args.privacy_status,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

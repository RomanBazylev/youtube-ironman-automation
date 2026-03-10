import math
import re
from typing import Dict, List


def _sentences(text: str) -> List[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text.strip())
    return [c.strip() for c in chunks if c.strip()]


def generate_scene_prompts(script: str, video_type: str) -> List[Dict[str, str | int]]:
    lines = _sentences(script)
    if not lines:
        lines = ["Discipline wins."]

    target_scene_duration = 2.5 if video_type == "short" else 3
    approx_total_s = max(20 if video_type == "short" else 60, int(len(script.split()) / 2.2))
    scene_count = max(8, math.ceil(approx_total_s / target_scene_duration))

    visuals = [
        "man training boxing",
        "cold morning run",
        "man journaling",
        "city sunrise",
        "man lifting weights",
        "focus eyes closeup",
        "business suit walking",
        "stormy ocean waves",
        "mountain peak",
        "empty gym",
    ]

    scenes: List[Dict[str, str | int]] = []
    for i in range(scene_count):
        text = lines[i % len(lines)]
        clean_caption = re.sub(r"[^A-Za-z0-9 '\-]", "", text).strip()
        if len(clean_caption) > 42:
            clean_caption = clean_caption[:42].rstrip() + "..."
        scenes.append(
            {
                "visual_keyword": visuals[i % len(visuals)],
                "duration": 2 if video_type == "short" else 3,
                "caption_text": clean_caption.upper(),
            }
        )
    return scenes

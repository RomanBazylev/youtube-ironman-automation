import math
import random
import re
from typing import Dict, List


def _sentences(text: str) -> List[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text.strip())
    return [c.strip() for c in chunks if c.strip()]


def generate_scene_prompts(script: str, video_type: str) -> List[Dict[str, str | int]]:
    lines = _sentences(script)
    if not lines:
        lines = ["Discipline wins."]

    target_scene_duration = 3
    # Natural edge-tts at +5% ≈ 2.5 wps; use 2.0 to guarantee enough video.
    approx_total_s = max(25 if video_type == "short" else 60, int(len(script.split()) / 2.0))
    scene_count = max(9, math.ceil(approx_total_s / target_scene_duration))

    # Diverse cinematic visuals — dark, moody, masculine atmosphere.
    visuals = [
        "man boxing training dark gym",
        "man running alone morning fog",
        "man journaling at wooden desk",
        "city skyline sunrise silhouette man",
        "man deadlift heavy weights gym",
        "intense male eyes closeup focus",
        "man suit walking city confident",
        "ocean waves dark dramatic",
        "man standing mountain summit alone",
        "empty gym dark moody lighting",
        "man meditating dark room calm",
        "man walking rain city night",
        "man reading book library alone",
        "chess pieces closeup strategy",
        "clock ticking time passing",
        "man pushups outdoor park dawn",
        "fire flames dark background cinematic",
        "man cold shower water face",
        "lion walking powerful majestic",
        "wolf lone dark forest",
        # Wealth & success
        "sports car dark garage",
        "luxury watch closeup dark",
        "stock market charts screen dark",
        "man typing laptop late night",
        "cash money dark background",
        "penthouse city view night",
        # Nature & power
        "eagle flying mountains dramatic",
        "storm clouds lightning dark sky",
        "waterfall jungle powerful flow",
        "dark road ahead foggy",
        "sunrise over mountains golden",
        "man walking desert alone heat",
        # Historical / warrior
        "ancient warrior statue dark",
        "samurai sword dark background",
        "roman colosseum dramatic sky",
        "spartan helmet dark cinematic",
        "old library books dark moody",
    ]

    # Shuffle visuals so consecutive videos look different.
    random.shuffle(visuals)

    scenes: List[Dict[str, str | int]] = []
    for i in range(scene_count):
        scenes.append(
            {
                "visual_keyword": visuals[i % len(visuals)],
                "duration": 3,
                "caption_text": "",  # Subtitles come from voice word-timestamps now.
            }
        )
    return scenes

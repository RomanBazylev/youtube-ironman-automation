import math
import random
import re
from typing import Dict, List

# Map script keywords to stock-search queries.
KEYWORD_VISUALS = {
    "prison": "man alone dark cell contemplation",
    "war": "soldier battlefield dramatic",
    "battle": "warrior combat dark cinematic",
    "spartan": "spartan helmet warrior statue",
    "samurai": "samurai sword dark background",
    "roman": "roman colosseum dramatic sky",
    "napoleon": "military general map strategy dark",
    "emperor": "ancient throne dark cinematic",
    "plague": "dark city fog epidemic moody",
    "journal": "man journaling wooden desk candle",
    "write": "man writing notebook dark room",
    "money": "cash money dark background",
    "wealth": "luxury office city night view",
    "broke": "empty wallet dark moody",
    "gym": "man deadlift heavy weights gym",
    "train": "man boxing training dark gym",
    "run": "man running alone morning fog",
    "sleep": "man waking up early dark room",
    "morning": "sunrise silhouette man city",
    "ocean": "ocean waves dark dramatic",
    "mountain": "man standing mountain summit",
    "meditat": "man meditating dark room calm",
    "father": "father son silhouette sunset",
    "son": "boy training discipline outdoor",
    "breakup": "man alone rain city night window",
    "heart": "man contemplative dark emotional",
    "silence": "empty room man alone quiet",
    "solitude": "man walking desert alone",
    "fear": "intense male eyes closeup dark",
    "focus": "man working laptop late night intense",
    "chess": "chess pieces closeup strategy dark",
    "clock": "clock ticking time passing dark",
    "fire": "fire flames dark background cinematic",
    "storm": "storm clouds lightning dark sky",
    "eagle": "eagle flying mountains dramatic",
    "lion": "lion walking powerful majestic",
    "wolf": "wolf lone dark forest",
    "tesla": "electric lightning inventor laboratory dark",
    "musk": "rocket launch night dramatic",
    "mandela": "prison bars hope light ray",
    "aurelius": "ancient roman statue philosophy",
    "seneca": "old library scrolls candle dark",
    "goggins": "ultramarathon runner pain endurance",
    "seal": "navy seal training water obstacle",
    "jordan": "university lecture hall serious",
    "kobe": "basketball court empty dark gym lights",
    "tyson": "boxing ring dark spotlight",
    "car": "sports car dark garage",
    "ship": "cargo ship ocean storm dramatic",
    "book": "man reading book library alone",
    "phone": "man putting phone away discipline",
    "game": "man closing laptop focus mode",
}

DEFAULT_VISUALS = [
    "man boxing training dark gym",
    "man running alone morning fog",
    "city skyline sunrise silhouette man",
    "intense male eyes closeup focus",
    "man standing mountain summit alone",
    "man walking rain city night",
    "fire flames dark background cinematic",
    "storm clouds lightning dark sky",
    "chess pieces closeup strategy",
    "man meditating dark room calm",
]


def _sentences(text: str) -> List[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text.strip())
    return [c.strip() for c in chunks if c.strip()]


def _visual_for_text(text: str, fallback_pool: List[str], index: int) -> str:
    lower = text.lower()
    for keyword, visual in KEYWORD_VISUALS.items():
        if keyword in lower:
            return visual
    return fallback_pool[index % len(fallback_pool)]


def generate_scene_prompts(script: str, video_type: str) -> List[Dict[str, str | int]]:
    lines = _sentences(script)
    if not lines:
        lines = ["Discipline wins."]

    target_scene_duration = 3
    approx_total_s = max(25 if video_type == "short" else 60, int(len(script.split()) / 2.0))
    scene_count = max(9, math.ceil(approx_total_s / target_scene_duration))

    fallback_pool = DEFAULT_VISUALS.copy()
    random.shuffle(fallback_pool)

    # Distribute script sentences across scenes for context-aware visuals.
    scenes: List[Dict[str, str | int]] = []
    for i in range(scene_count):
        line_idx = int(i * len(lines) / scene_count)
        chunk = lines[min(line_idx, len(lines) - 1)]
        # Include neighboring sentence for richer keyword matching.
        context = chunk
        if line_idx + 1 < len(lines):
            context += " " + lines[line_idx + 1]

        scenes.append({
            "visual_keyword": _visual_for_text(context, fallback_pool, i),
            "duration": 3,
            "caption_text": "",
        })

    return scenes

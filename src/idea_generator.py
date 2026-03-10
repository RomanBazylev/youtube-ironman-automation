import json
import random
import re
from typing import Dict

from src.llm_client import chat_json


FALLBACK_TOPICS = [
    "male psychology",
    "discipline",
    "self improvement",
    "stoicism",
    "mental toughness",
    "success mindset",
]

FALLBACK_HOOKS = [
    "Weak men ignore this until it destroys them.",
    "The truth about discipline nobody wants to hear.",
    "Strong men do this when no one is watching.",
]

WEAK_WORDS = {"maybe", "could", "sometimes", "thing", "stuff", "probably"}
POWER_WORDS = {
    "brutal",
    "truth",
    "discipline",
    "strong",
    "weak",
    "silent",
    "mindset",
    "focus",
    "stoic",
    "hard",
    "power",
    "respect",
    "control",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def _title_similarity(a: str, b: str) -> float:
    wa = set(_normalize_text(a).split())
    wb = set(_normalize_text(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def _score_hook(hook: str) -> float:
    words = _normalize_text(hook).split()
    if not words:
        return -999
    power = sum(1 for w in words if w in POWER_WORDS)
    weak = sum(1 for w in words if w in WEAK_WORDS)
    length_penalty = abs(len(words) - 9) * 0.25
    return power * 1.5 - weak * 1.0 - length_penalty


def _one_idea(force_type: str | None = None) -> Dict[str, str]:
    prompt = (
        "Generate one viral faceless commentary YouTube idea in JSON with keys: "
        "title, hook, topic, video_type. video_type must be 'short' or 'normal'. "
        "Themes: male psychology, discipline, self improvement, stoicism, "
        "mental toughness, success mindset. Use provocative angle."
    )

    try:
        raw = chat_json(
            system_prompt="You generate viral but safe YouTube faceless commentary ideas.",
            user_prompt=prompt,
            temperature=0.9,
        )
        obj = json.loads(raw)
        video_type = (force_type or obj.get("video_type", "short")).lower()
        if video_type not in {"short", "normal"}:
            video_type = "short"
        return {
            "title": obj.get("title", "7 Brutal Truths Weak Men Avoid").strip(),
            "hook": obj.get("hook", random.choice(FALLBACK_HOOKS)).strip(),
            "topic": obj.get("topic", random.choice(FALLBACK_TOPICS)).strip(),
            "video_type": video_type,
        }
    except Exception:
        fallback_type = force_type if force_type in {"short", "normal"} else "short"
        topic = random.choice(FALLBACK_TOPICS)
        return {
            "title": "7 Brutal Truths Weak Men Avoid",
            "hook": random.choice(FALLBACK_HOOKS),
            "topic": topic,
            "video_type": fallback_type,
        }


def generate_video_idea(
    force_type: str | None = None,
    recent_titles: list[str] | None = None,
    candidates: int = 3,
) -> Dict[str, str]:
    recent_titles = recent_titles or []
    pool = [_one_idea(force_type=force_type) for _ in range(max(1, candidates))]

    best = pool[0]
    best_score = -10_000.0
    for idea in pool:
        sim_penalty = 0.0
        for rt in recent_titles:
            sim_penalty = max(sim_penalty, _title_similarity(idea["title"], rt))

        score = _score_hook(idea["hook"]) - sim_penalty * 4.0
        if score > best_score:
            best = idea
            best_score = score

    return best

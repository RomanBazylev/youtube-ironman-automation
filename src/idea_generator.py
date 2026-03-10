import json
import random
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


def generate_video_idea(force_type: str | None = None) -> Dict[str, str]:
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

import json
from typing import Dict
from config.settings import GROQ_API_KEY, OPENAI_API_KEY, VIDEO_SPECS
from src.llm_client import chat_json


def generate_script(idea: Dict[str, str]) -> Dict[str, str]:
    video_type = idea["video_type"]
    spec = VIDEO_SPECS[video_type]
    prompt = (
        "Return JSON with keys: script, seo_title, seo_description, tags. "
        f"Length: {spec.min_words}-{spec.max_words} words. "
        "Script structure: hook, points, conclusion CTA. "
        "Use short punchy sentences and one-line paragraphs. "
        f"Topic: {idea['topic']}. Hook seed: {idea['hook']}."
    )

    if not GROQ_API_KEY and not OPENAI_API_KEY:
        script = (
            f"{idea['hook']} Discipline is boring. That is why it works. "
            "Weak men chase motivation. Strong men build systems. "
            "Wake up early. Train hard. Keep promises to yourself. "
            "Silence your excuses. Stack one hard win every day. "
            "In 90 days your identity changes. Save this and start today."
        )
        return {
            "script": script,
            "seo_title": idea["title"],
            "seo_description": "Faceless commentary on discipline and mental toughness.",
            "tags": ["discipline", "selfimprovement", "stoicism", "mindset"],
        }

    try:
        raw = chat_json(
            system_prompt="Write concise, high-retention faceless commentary scripts.",
            user_prompt=prompt,
            temperature=0.8,
        )
        obj = json.loads(raw)
        tags = obj.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        script = obj["script"].strip()
        word_count = len(script.split())
        if word_count < spec.min_words * 0.7 or word_count > spec.max_words * 1.3:
            print(f"[SCRIPT] LLM returned {word_count} words (spec {spec.min_words}-{spec.max_words}), using fallback")
            raise ValueError("Script word count out of range")

        return {
            "script": script,
            "seo_title": obj.get("seo_title", idea["title"]).strip(),
            "seo_description": obj.get("seo_description", idea["hook"]).strip(),
            "tags": tags[:15],
        }
    except Exception:
        return {
            "script": (
                f"{idea['hook']} Weak men wait for the perfect mood. "
                "Strong men act when they are tired. "
                "Discipline is choosing long-term respect over short-term comfort. "
                "Train your body. Guard your mind. Keep your word. "
                "Your future is built in silent mornings."
            ),
            "seo_title": idea["title"],
            "seo_description": "Practical self-improvement commentary for men.",
            "tags": ["discipline", "selfimprovement", "mentalstrength"],
        }

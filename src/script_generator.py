import json
from typing import Dict
from config.settings import GROQ_API_KEY, OPENAI_API_KEY, VIDEO_SPECS
from src.llm_client import chat_json


def generate_script(idea: Dict[str, str]) -> Dict[str, str]:
    video_type = idea["video_type"]
    spec = VIDEO_SPECS[video_type]

    if video_type == "longform":
        prompt = (
            "Return JSON with keys: script, seo_title, seo_description, tags.\n"
            f"Script length: exactly {spec.min_words}-{spec.max_words} words.\n"
            "Channel style: masculine, authoritative narrator — like a documentary.\n"
            "Script rules:\n"
            "- This is an 8-12 minute deep-dive video about a real person or philosophy.\n"
            "- Structure: Hook (shocking opening) → Origin (early life/background) → "
            "Struggle (failures, setbacks) → Turning Point (key moment) → Rise "
            "(achievements, transformation) → Lessons (what we can learn) → Outro.\n"
            "- Use short punchy sentences. Max 15 words per sentence.\n"
            "- Include specific dates, numbers, quotes from the person.\n"
            "- Build tension and narrative arc — this is storytelling, not advice.\n"
            "- Speak directly to 'you' only in the lessons section.\n"
            "- Tone: serious, cinematic, respectful but intense.\n"
            "- NO emojis, NO hashtags in script.\n"
            f"Topic: {idea['topic']}. Hook seed: {idea['hook']}.\n"
            "seo_title: max 70 chars, compelling and includes person's name.\n"
            "seo_description: 3-4 sentences about the story. Include 'full story'.\n"
            "tags: list of 10-15 relevant tags including person's name."
        )
    else:
        prompt = (
            "Return JSON with keys: script, seo_title, seo_description, tags.\n"
            f"Script length: exactly {spec.min_words}-{spec.max_words} words.\n"
            "Channel style: masculine, direct, motivational commentary for men.\n"
            "Script rules:\n"
            "- First sentence MUST be a provocative hook that stops the scroll.\n"
            "- Use short punchy sentences. Max 12 words per sentence.\n"
            "- One idea per sentence. No filler words.\n"
            "- Speak directly to 'you'. Be commanding, not preachy.\n"
            "- Include concrete examples: wake up at 5am, cold shower, gym at 6.\n"
            "- End with a strong call-to-action: follow, save, share.\n"
            "- Tone: confident, calm authority. Like a mentor, not a drill sergeant.\n"
            "- NO emojis, NO hashtags in the script, NO questions.\n"
            f"Topic: {idea['topic']}. Hook seed: {idea['hook']}.\n"
            "seo_title: max 70 chars, clickbait but honest. Include power words.\n"
            "seo_description: 2-3 sentences summarizing the message.\n"
            "tags: list of 8-12 relevant single-word or two-word tags."
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

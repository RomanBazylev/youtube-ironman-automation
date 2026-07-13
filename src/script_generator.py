import json
import random
from typing import Dict, List

from config.settings import GROQ_API_KEY, OPENAI_API_KEY, VIDEO_SPECS
from src.llm_client import chat_json


SCRIPT_STYLES = [
    {
        "name": "story_arc",
        "instruction": (
            "Open with a micro-story (2-3 sentences) about a real person. "
            "Build tension, reveal the lesson, end with one actionable step."
        ),
    },
    {
        "name": "contrarian",
        "instruction": (
            "Challenge a popular belief in the first sentence. "
            "Present evidence, then offer a sharper alternative mindset."
        ),
    },
    {
        "name": "experiment",
        "instruction": (
            "Frame as a personal test: 'I tried X for N days.' "
            "Share what changed — be specific about feelings and results."
        ),
    },
    {
        "name": "quote_led",
        "instruction": (
            "Start with a real quote from a historical figure. "
            "Unpack what it means today with one modern example."
        ),
    },
    {
        "name": "data_driven",
        "instruction": (
            "Lead with a surprising number or study result. "
            "Connect it to daily habits men can control."
        ),
    },
]

FALLBACK_SCRIPTS = [
    (
        "{hook} Comfort trains weakness. Discomfort trains power. "
        "You do not need motivation. You need a standard. "
        "Wake before excuses. Move before doubt. "
        "Repeat until your identity changes. Start tonight."
    ),
    (
        "{hook} Most men negotiate with themselves every morning. "
        "Winners stopped negotiating years ago. "
        "They chose a routine and defended it like rent. "
        "Your calendar reveals your priorities. Fix that first."
    ),
    (
        "{hook} Respect is not requested. It is accumulated. "
        "One kept promise at a time. One hard conversation at a time. "
        "Silence the noise. Build the man you said you would become."
    ),
]


def _build_short_prompt(idea: Dict[str, str], spec) -> str:
    style = random.choice(SCRIPT_STYLES)
    angle = idea.get("angle", "uncomfortable truths")
    fmt = idea.get("format", "one counterintuitive lesson")
    audience = idea.get("audience", "ambitious men")

    return (
        "Return JSON with keys: script, seo_title, seo_description, tags.\n"
        f"Script length: {spec.min_words}-{spec.max_words} words.\n"
        "Channel: masculine faceless commentary — calm authority, not shouting.\n\n"
        f"STYLE: {style['name']} — {style['instruction']}\n"
        f"ANGLE: {angle}\n"
        f"FORMAT: {fmt}\n"
        f"TARGET AUDIENCE: {audience}\n"
        f"Topic: {idea['topic']}\n"
        f"Hook seed: {idea['hook']}\n\n"
        "SCRIPT RULES:\n"
        "- First sentence MUST hook instantly — vary structure (not always 'The...').\n"
        "- Short punchy sentences. Max 12 words each.\n"
        "- One idea per sentence. Zero filler.\n"
        "- Use 'you' sparingly — max 3 times total.\n"
        "- Include ONE concrete detail: time, place, number, or name.\n"
        "- DO NOT repeat clichés: 'weak men vs strong men', 'cold shower at 5am', "
        "'nobody tells young men', 'discipline is boring'.\n"
        "- DO NOT start more than 2 sentences the same way.\n"
        "- End with a direct CTA (follow, save, or try one action today).\n"
        "- NO emojis, NO hashtags in script.\n\n"
        "seo_title: max 65 chars, specific and click-worthy.\n"
        "seo_description: 2-3 sentences, unique to this topic.\n"
        "tags: 8-12 diverse tags — NOT just discipline/selfimprovement/mentalstrength."
    )


def _build_longform_prompt(idea: Dict[str, str], spec) -> str:
    return (
        "Return JSON with keys: script, seo_title, seo_description, tags.\n"
        f"Script length: {spec.min_words}-{spec.max_words} words.\n"
        "Channel style: masculine, authoritative narrator — documentary tone.\n"
        "Script rules:\n"
        "- 8-12 minute deep-dive about a real person or philosophy.\n"
        "- Structure: Hook → Origin → Struggle → Turning Point → Rise → Lessons → Outro.\n"
        "- Short punchy sentences. Max 15 words per sentence.\n"
        "- Include specific dates, numbers, real quotes.\n"
        "- Build narrative tension — storytelling, not generic advice.\n"
        "- Use 'you' only in the lessons section.\n"
        "- Tone: serious, cinematic, respectful but intense.\n"
        "- NO emojis, NO hashtags in script.\n"
        f"Topic: {idea['topic']}. Hook seed: {idea['hook']}.\n"
        "seo_title: max 70 chars, includes person's name.\n"
        "seo_description: 3-4 sentences about the story.\n"
        "tags: 10-15 relevant tags including person's name."
    )


def _fallback_result(idea: Dict[str, str]) -> Dict[str, str]:
    template = random.choice(FALLBACK_SCRIPTS)
    return {
        "script": template.format(hook=idea["hook"]),
        "seo_title": idea.get("title", idea["hook"])[:65],
        "seo_description": f"A focused take on {idea['topic']}.",
        "tags": _diverse_tags(idea),
    }


def _diverse_tags(idea: Dict[str, str]) -> List[str]:
    base = ["discipline", "mindset", "selfimprovement"]
    topic_words = [w for w in idea.get("topic", "").lower().split() if len(w) > 4][:5]
    extra = ["mentalstrength", "motivation", "masculinity", "stoicism", "success"]
    tags = list(dict.fromkeys(base + topic_words + random.sample(extra, 3)))
    return tags[:12]


def generate_script(idea: Dict[str, str]) -> Dict[str, str]:
    video_type = idea["video_type"]
    spec = VIDEO_SPECS[video_type]

    if video_type == "longform":
        prompt = _build_longform_prompt(idea, spec)
    else:
        prompt = _build_short_prompt(idea, spec)

    if not GROQ_API_KEY and not OPENAI_API_KEY:
        return _fallback_result(idea)

    try:
        raw = chat_json(
            system_prompt=(
                "Write high-retention faceless commentary scripts. "
                "Every script must feel unique — vary structure, vocabulary, and rhythm. "
                "Never produce generic motivational filler."
            ),
            user_prompt=prompt,
            temperature=0.9,
        )
        obj = json.loads(raw)
        tags = obj.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        if len(tags) < 4:
            tags = _diverse_tags(idea)

        script = obj["script"].strip()
        word_count = len(script.split())
        # Relaxed bounds — strict validation was causing too many fallbacks.
        if word_count < spec.min_words * 0.55 or word_count > spec.max_words * 1.5:
            print(
                f"[SCRIPT] LLM returned {word_count} words "
                f"(spec {spec.min_words}-{spec.max_words}), using fallback"
            )
            raise ValueError("Script word count out of range")

        return {
            "script": script,
            "seo_title": obj.get("seo_title", idea.get("title", idea["hook"])).strip()[:70],
            "seo_description": obj.get("seo_description", idea["hook"]).strip(),
            "tags": tags[:15],
        }
    except Exception as exc:
        print(f"[SCRIPT] Generation failed: {exc}")
        return _fallback_result(idea)

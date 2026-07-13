import json
import random
import re
from typing import Dict, List

from src.llm_client import chat_json


FALLBACK_TOPICS = [
    # Classic pillars
    "male psychology",
    "discipline",
    "self improvement",
    "stoicism",
    "mental toughness",
    "success mindset",
    "emotional control",
    "purpose and mission",
    "loneliness in men",
    "confidence building",
    "habits of winners",
    "handling rejection",
    "accountability",
    "financial discipline",
    "silent leadership",
    # Money & career
    "building wealth from zero",
    "side hustle mindset",
    "investing for beginners",
    "negotiation skills",
    "quitting a dead-end job",
    "passive income strategies",
    "the psychology of money",
    "lessons from billionaires",
    # Health & body
    "cold exposure and mental toughness",
    "sleep optimization for peak performance",
    "training like a warrior",
    "nutrition for sharp thinking",
    "testosterone and lifestyle",
    "the power of fasting",
    # Relationships & social
    "how strong men handle conflict",
    "boundaries in relationships",
    "what high-quality women look for",
    "how to earn respect without speaking",
    "body language of powerful men",
    "the art of walking away",
    "being a better father",
    # History & philosophy
    "Marcus Aurelius and modern leadership",
    "lessons from Spartans",
    "samurai principles for modern men",
    "Miyamoto Musashi's Book of Five Rings",
    "lessons from military generals",
    "ancient Greek ideas about manhood",
    "Nietzsche's will to power",
    "Sun Tzu's Art of War for daily life",
    # Mindset & psychology
    "why comfort is killing you",
    "the danger of comparison",
    "how to stop overthinking",
    "dealing with toxic people",
    "fear of failure vs fear of mediocrity",
    "the power of solitude",
    "delayed gratification and success",
    "reprogramming your subconscious mind",
    # Real-world stories
    "how David Goggins transformed himself",
    "Elon Musk's insane work ethic",
    "Jocko Willink on extreme ownership",
    "how Kobe Bryant outworked everyone",
    "Arnold Schwarzenegger's 6 rules of success",
    "Mike Tyson on discipline and fear",
    "lessons from Navy SEAL training",
    "how Floyd Mayweather built an empire",
]

LONGFORM_TOPICS = [
    # Real transformation stories
    "How David Goggins went from 300 lbs exterminator to Navy SEAL",
    "Arnold Schwarzenegger's journey from Austrian village to Hollywood legend",
    "Kobe Bryant's Mamba Mentality — the full story behind the obsession",
    "Jocko Willink and the Battle of Ramadi — leadership forged in combat",
    "How Mike Tyson became the youngest heavyweight champion at 20",
    "Elon Musk's path from bullied kid in South Africa to Mars visionary",
    "Marcus Aurelius — the philosopher emperor who ruled during plague",
    "How Miyamoto Musashi won 61 duels and wrote the Book of Five Rings",
    "The rise and fall and rise of Floyd Mayweather",
    "How Nelson Mandela spent 27 years in prison and emerged a leader",
    "Nikola Tesla's tragic genius — the man who lit the world",
    "Bruce Lee's philosophy — be water and the art of no limitation",
    "How Andrew Carnegie went from factory boy to richest man alive",
    "Theodore Roosevelt — the sickly boy who became the toughest president",
    "The Spartan 300 — what really happened at Thermopylae",
    "How Alexander the Great conquered the known world by age 30",
    "Genghis Khan — from orphaned outcast to ruler of the largest empire",
    "How Keanu Reeves handled tragedy and became Hollywood's most loved",
    "The untold story of Dwayne Johnson's depression and comeback",
    "How Jim Carrey went from living in a van to $20 million per film",
    "Steve Jobs fired from his own company — and how he came back stronger",
    "How Michael Jordan used failure as fuel for 6 championships",
    "Conor McGregor — from plumber on welfare to UFC double champion",
    "How Goggins ran 100 miles with broken feet — and what it teaches",
    "The philosophy of Seneca — wealth, exile, and Stoic mastery",
    "How Walt Disney was fired for lacking imagination then built an empire",
    "The complete story of Navy SEAL Hell Week — who survives and why",
    "Viktor Frankl — finding meaning in Auschwitz concentration camp",
    "How Cristiano Ronaldo's obsessive work ethic made him the GOAT",
    "The samurai code of Bushido — 7 virtues that built warriors",
]

FALLBACK_HOOKS = [
    "Weak men ignore this until it destroys them.",
    "The truth about discipline nobody wants to hear.",
    "Strong men do this when no one is watching.",
    "Most men will never recover from this mistake.",
    "This one habit separates leaders from followers.",
    "Nobody tells young men this — and it ruins them.",
    "If you feel lost in your 20s, watch this now.",
    "The dark truth about comfort zones.",
    "Why average men stay average forever.",
    "Stop doing this and your life changes in 30 days.",
    "Your bank account reflects your discipline.",
    "This is why you are always tired.",
    "The strongest men in history all did this.",
    "Most men quit right before the breakthrough.",
    "One cold shower taught me more than 4 years of college.",
    "The silent habit that builds empires.",
    "Rich men never say this out loud.",
    "A lion does not lose sleep over the opinions of sheep.",
    "Your morning routine is either building you or breaking you.",
    "Loneliness is not the problem. Weakness is.",
]

ANGLES = [
    "uncomfortable truths",
    "common mistakes men make",
    "what high-value men do differently",
    "lessons from ancient warriors",
    "psychological tricks for dominance",
    "how modern society weakens men",
    "things men learn too late",
    "silent rules of respect",
    "why most men fail at discipline",
    "mindset shifts that create winners",
    "the price of being soft",
    "dark psychology of success",
    "what your father never taught you",
    "signs you are mentally weak",
    "how to rebuild yourself from nothing",
    "why loneliness is a superpower",
    "the stoic response to chaos",
    "habits that destroy men slowly",
    "what women secretly respect in men",
    "rules every man should live by",
    "how to stop caring what people think",
    "why pain is necessary for growth",
]

FORMATS = [
    "personal experiment (I tried X for 30 days)",
    "one counterintuitive lesson from history",
    "myth vs reality about a famous man",
    "before vs after mindset shift",
    "day-in-the-life contrast (average vs disciplined)",
    "historical story + one modern application",
    "countdown (worst habit to best habit)",
    "unpopular opinion with evidence",
    "character study of a real leader",
    "if-then consequences of one decision",
    "challenge or dare to the viewer",
    "step-by-step transformation blueprint",
    "comparison (reactive vs proactive response)",
    "quote-led narrative (start with real quote)",
    "data-driven insight (specific number or study)",
]

# Formats that performed well historically on this channel.
PROVEN_FORMATS = [
    "personal experiment (I tried X for 30 days)",
    "historical story + one modern application",
    "quote-led narrative (start with real quote)",
    "one counterintuitive lesson from history",
]

TARGET_AUDIENCES = [
    "men in their 20s figuring life out",
    "men recovering from failure",
    "introverted men who feel overlooked",
    "men stuck in dead-end routines",
    "ambitious men who lack discipline",
    "men going through a breakup",
    "men who want to command respect",
    "young professionals under pressure",
    "men who overthink everything",
    "fathers trying to set an example",
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


def _figure_overlap(text: str, banned: List[str]) -> int:
    lower = _normalize_text(text)
    return sum(1 for fig in banned if fig in lower)


def _pattern_overlap(text: str, banned: List[str]) -> int:
    lower = _normalize_text(text)
    return sum(1 for pat in banned if pat in lower)


def _pick_format() -> str:
    if random.random() < 0.45:
        return random.choice(PROVEN_FORMATS)
    return random.choice(FORMATS)


def _one_idea(
    force_type: str | None = None,
    content_signals: dict | None = None,
) -> Dict[str, str]:
    content_signals = content_signals or {}
    angle = random.choice(ANGLES)
    fmt = _pick_format()
    audience = random.choice(TARGET_AUDIENCES)

    avoid_figures = content_signals.get("overused_figures", [])
    avoid_patterns = content_signals.get("overused_patterns", [])
    winning_titles = content_signals.get("winning_titles", [])

    avoid_block = ""
    if avoid_figures:
        avoid_block += f"\nAVOID these overused figures: {', '.join(avoid_figures)}."
    if avoid_patterns:
        avoid_block += f"\nAVOID these overused title patterns: {', '.join(avoid_patterns)}."
    if winning_titles:
        avoid_block += (
            "\nThese titles performed well — match their SPECIFICITY, not their wording: "
            + "; ".join(winning_titles[:3])
        )

    prompt = (
        "Generate one viral faceless commentary YouTube idea in JSON with keys: "
        "title, hook, topic, video_type. video_type must be 'short' or 'normal'. "
        "Themes: male psychology, discipline, self improvement, stoicism, "
        "mental toughness, success mindset, wealth building, health optimization, "
        "ancient wisdom, famous leaders, relationship dynamics, productivity.\n\n"
        f"ANGLE: {angle}\n"
        f"FORMAT: {fmt}\n"
        f"TARGET AUDIENCE: {audience}\n"
        f"{avoid_block}\n\n"
        "CRITICAL RULES:\n"
        "- Make the topic UNIQUE and SPECIFIC. No generic '7 Brutal Truths' titles.\n"
        "- Use a real person, a real study, a specific number, or a concrete habit.\n"
        "- Do NOT reuse cliché formulas like 'The X-Word Phrase', 'The X% Rule', "
        "'4-Hour Work Window', 'Weak Men vs Strong Men'.\n"
        "- Vary the opening: story, quote, statistic, confession, or challenge — not always 'The...'.\n"
        "- Hook must feel fresh — not 'Most men will never...' or 'Nobody tells young men...'.\n"
        "- Title max 65 chars, punchy and specific.\n"
        "Be provocative but safe for YouTube."
    )

    if force_type == "longform":
        lf_topic = random.choice(LONGFORM_TOPICS)
        prompt = (
            "Generate one viral long-form faceless commentary YouTube idea in JSON "
            "with keys: title, hook, topic, video_type. video_type MUST be 'longform'.\n"
            "This is an 8-12 minute deep-dive video about a real person's journey, "
            "transformation, or philosophy.\n\n"
            f"TOPIC SEED: {lf_topic}\n"
            f"ANGLE: {angle}\n"
            f"TARGET AUDIENCE: {audience}\n"
            f"{avoid_block}\n\n"
            "RULES:\n"
            "- Title must be compelling, specific, and include the person's name.\n"
            "- Hook must be a single shocking sentence that stops the viewer.\n"
            "- Topic must be a SPECIFIC real story, not generic advice.\n"
            "- Think of this as a mini-documentary narration, not a motivational clip.\n"
            "Be provocative but safe for YouTube."
        )

    try:
        raw = chat_json(
            system_prompt="You generate viral but safe YouTube faceless commentary ideas.",
            user_prompt=prompt,
            temperature=0.95,
        )
        obj = json.loads(raw)
        video_type = (force_type or obj.get("video_type", "short")).lower()
        if video_type not in {"short", "normal", "longform"}:
            video_type = "short"
        return {
            "title": obj.get("title", "7 Brutal Truths Weak Men Avoid").strip(),
            "hook": obj.get("hook", random.choice(FALLBACK_HOOKS)).strip(),
            "topic": obj.get("topic", random.choice(FALLBACK_TOPICS)).strip(),
            "video_type": video_type,
            "angle": angle,
            "format": fmt,
            "audience": audience,
        }
    except Exception:
        fallback_type = force_type if force_type in {"short", "normal", "longform"} else "short"
        topics = LONGFORM_TOPICS if fallback_type == "longform" else FALLBACK_TOPICS
        try:
            from analytics import get_topic_weights
            weights = get_topic_weights(topics)
            if weights:
                topic = random.choices(topics, weights=weights, k=1)[0]
            else:
                topic = random.choice(topics)
        except Exception:
            topic = random.choice(topics)
        hook = random.choice(FALLBACK_HOOKS)
        return {
            "title": hook[:65],
            "hook": hook,
            "topic": topic,
            "video_type": fallback_type,
            "angle": angle,
            "format": fmt,
            "audience": audience,
        }


def generate_video_idea(
    force_type: str | None = None,
    recent_titles: list[str] | None = None,
    candidates: int = 6,
    content_signals: dict | None = None,
) -> Dict[str, str]:
    recent_titles = recent_titles or []
    if content_signals is None:
        try:
            from analytics import get_recent_content_signals
            content_signals = get_recent_content_signals()
            recent_titles = list(dict.fromkeys(recent_titles + content_signals.get("recent_titles", [])))
        except Exception:
            content_signals = {}

    pool = [
        _one_idea(force_type=force_type, content_signals=content_signals)
        for _ in range(max(1, candidates))
    ]

    overused_figures = content_signals.get("overused_figures", [])
    overused_patterns = content_signals.get("overused_patterns", [])

    best = pool[0]
    best_score = -10_000.0
    for idea in pool:
        sim_penalty = 0.0
        for rt in recent_titles:
            sim_penalty = max(sim_penalty, _title_similarity(idea["title"], rt))
            sim_penalty = max(sim_penalty, _title_similarity(idea["topic"], rt) * 0.7)

        figure_penalty = _figure_overlap(idea["title"] + " " + idea["topic"], overused_figures) * 2.5
        pattern_penalty = _pattern_overlap(idea["title"], overused_patterns) * 3.0

        # Penalize generic short titles
        title_words = len(_normalize_text(idea["title"]).split())
        generic_penalty = 2.0 if title_words <= 2 else 0.0

        score = (
            _score_hook(idea["hook"])
            - sim_penalty * 4.0
            - figure_penalty
            - pattern_penalty
            - generic_penalty
        )
        if score > best_score:
            best = idea
            best_score = score

    return best

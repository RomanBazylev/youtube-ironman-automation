import asyncio
import json
import random
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple

import edge_tts
import requests

from config.settings import OPENAI_API_KEY


# Deep male voices — same set proven across reddit-stories, salesforce, fishing projects.
TTS_VOICES = [
    "en-US-GuyNeural",
    "en-US-AndrewMultilingualNeural",
    "en-US-BrianMultilingualNeural",
]
TTS_RATE_OPTIONS = ["+0%", "+3%", "+5%", "+7%"]

# OpenAI TTS fallback — deep male voice.
OPENAI_TTS_VOICE = "onyx"
OPENAI_TTS_MODEL = "tts-1"


def _probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def _estimate_word_events(text: str, total_duration: float) -> List[Dict]:
    """Estimate word timestamps with sentence-aware distribution.

    Splits text into sentences, allocates time proportionally by word count,
    inserts inter-sentence gaps, and distributes words evenly within each sentence.
    This significantly reduces cumulative drift vs. naive uniform distribution.
    """
    words = text.split()
    if not words:
        return []

    # Split into sentences on . ! ? (keep short fragments together).
    import re as _re
    raw_sentences = _re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in raw_sentences if s.split()]
    if not sentences:
        sentences = [text]

    total_words = sum(len(s.split()) for s in sentences)
    if total_words == 0:
        return []

    inter_sentence_gap = 0.25
    total_gap_time = inter_sentence_gap * max(0, len(sentences) - 1)
    available_speech = max(0.5, total_duration - total_gap_time)

    events: List[Dict] = []
    cursor = 0.0
    for idx, sentence in enumerate(sentences):
        s_words = sentence.split()
        if not s_words:
            continue
        # Allocate time proportionally to word count.
        s_duration = available_speech * (len(s_words) / total_words)
        w_dur = s_duration / len(s_words)
        for w in s_words:
            events.append({"text": w, "offset": cursor, "duration": w_dur * 0.9})
            cursor += w_dur
        # Add gap between sentences (not after the last one).
        if idx < len(sentences) - 1:
            cursor += inter_sentence_gap

    print(f"[VOICE] WARNING: using estimated timestamps ({len(events)} words, {len(sentences)} sentences)")
    return events


def _generate_openai_tts(text: str, output_path: Path) -> List[Dict]:
    """Fallback: generate via OpenAI TTS API. Returns estimated word events."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured — cannot use TTS fallback")

    resp = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_TTS_MODEL,
            "voice": OPENAI_TTS_VOICE,
            "input": text,
        },
        timeout=120,
    )
    resp.raise_for_status()
    output_path.write_bytes(resp.content)

    dur = _probe_duration(output_path)
    word_events = _estimate_word_events(text, dur)
    print(f"[VOICE] OpenAI TTS fallback — {len(word_events)} words — {dur:.1f}s")
    return word_events


async def _generate_with_word_boundaries(
    text: str, output_path: Path, voice: str, rate: str,
) -> List[Dict]:
    """Generate TTS and capture WordBoundary events for subtitle sync."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    word_events: List[Dict] = []

    with open(str(output_path), "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_events.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"] / 10_000_000,  # 100-ns ticks → seconds
                    "duration": chunk["duration"] / 10_000_000,
                })

    return word_events


def generate_voiceover(script: str, output_path: Path) -> Tuple[Path, List[Dict]]:
    """Generate voiceover and return (audio_path, word_timestamps).

    Primary: edge-tts (free, word-level timestamps).
    Fallback: OpenAI TTS API (paid, estimated timestamps).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    voice = random.choice(TTS_VOICES)
    rate = random.choice(TTS_RATE_OPTIONS)

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            word_events = asyncio.run(
                _generate_with_word_boundaries(script, output_path, voice, rate)
            )
            dur = _probe_duration(output_path)
            if dur < 3.0:
                raise RuntimeError(f"Voice too short ({dur:.1f}s)")

            # Guard: edge-tts may succeed but emit zero WordBoundary events.
            if not word_events and dur >= 3.0:
                print(f"[VOICE] WARNING: edge-tts returned 0 word boundaries — using estimated timestamps")
                word_events = _estimate_word_events(script, dur)

            print(f"[VOICE] {voice} rate={rate} — {len(word_events)} words — {dur:.1f}s")

            ts_path = output_path.with_suffix(".words.json")
            ts_path.write_text(json.dumps(word_events, indent=2), encoding="utf-8")

            return output_path, word_events
        except Exception as e:
            last_error = e
            print(f"[VOICE] edge-tts attempt {attempt} ({voice}) failed: {e}")
            voice = random.choice(TTS_VOICES)
            rate = random.choice(TTS_RATE_OPTIONS)
            time.sleep(attempt)

    # Fallback to OpenAI TTS.
    print(f"[VOICE] edge-tts failed after 3 attempts, trying OpenAI TTS fallback...")
    try:
        word_events = _generate_openai_tts(script, output_path)

        ts_path = output_path.with_suffix(".words.json")
        ts_path.write_text(json.dumps(word_events, indent=2), encoding="utf-8")

        return output_path, word_events
    except Exception as fallback_err:
        print(f"[VOICE] OpenAI TTS fallback also failed: {fallback_err}")
        raise RuntimeError(
            f"All TTS engines failed. edge-tts: {last_error} | OpenAI: {fallback_err}"
        )

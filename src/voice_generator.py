import asyncio
import json
import random
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple

import edge_tts


# Deep male voices — same set proven across reddit-stories, salesforce, fishing projects.
TTS_VOICES = [
    "en-US-GuyNeural",
    "en-US-AndrewMultilingualNeural",
    "en-US-BrianMultilingualNeural",
]
TTS_RATE_OPTIONS = ["+0%", "+3%", "+5%", "+7%"]


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


async def _generate_with_word_boundaries(
    text: str, output_path: Path, voice: str, rate: str,
) -> List[Dict]:
    """Generate TTS and capture WordBoundary events for subtitle sync."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
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

    word_timestamps: list of {"text": str, "offset": float, "duration": float}
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
            print(f"[VOICE] {voice} rate={rate} — {len(word_events)} words — {dur:.1f}s")

            # Save word timestamps alongside audio for debugging.
            ts_path = output_path.with_suffix(".words.json")
            ts_path.write_text(json.dumps(word_events, indent=2), encoding="utf-8")

            return output_path, word_events
        except Exception as e:
            last_error = e
            print(f"[VOICE] attempt {attempt} ({voice}) failed: {e}")
            voice = random.choice(TTS_VOICES)
            rate = random.choice(TTS_RATE_OPTIONS)
            time.sleep(attempt)

    raise RuntimeError(f"Voice generation failed after 3 attempts. Last error: {last_error}")

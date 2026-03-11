import asyncio
import subprocess
import time
from pathlib import Path

import edge_tts
from gtts import gTTS


# Authoritative male voices — natural rate for motivational delivery.
# GuyNeural: deep & commanding.  AndrewMultilingual: clear & engaging.
# BrianMultilingual: smooth narrator.  RyanNeural: confident British.
VOICE_PROFILES = [
    {"voice": "en-US-GuyNeural", "rate": "+5%", "pitch": "+0Hz"},
    {"voice": "en-US-AndrewMultilingualNeural", "rate": "+5%", "pitch": "+0Hz"},
    {"voice": "en-US-BrianMultilingualNeural", "rate": "+5%", "pitch": "+0Hz"},
    {"voice": "en-GB-RyanNeural", "rate": "+5%", "pitch": "+0Hz"},
]


async def _edge_speak(text: str, output_path: Path, voice: str, rate: str, pitch: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))


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


def generate_voiceover(script: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt, profile in enumerate(VOICE_PROFILES, start=1):
        try:
            asyncio.run(
                _edge_speak(
                    script,
                    output_path,
                    voice=profile["voice"],
                    rate=profile["rate"],
                    pitch=profile["pitch"],
                )
            )
            dur = _probe_duration(output_path)
            if dur < 5.0:
                raise RuntimeError(f"Voice too short ({dur:.1f}s), retrying")
            print(f"[VOICE] {profile['voice']} OK — {dur:.1f}s")
            return output_path
        except Exception as e:
            last_error = e
            print(f"[VOICE] edge-tts attempt {attempt} failed: {e}")
            time.sleep(attempt)

    # Fallback keeps pipeline alive if edge-tts is blocked (e.g., 403 handshake).
    try:
        gTTS(text=script, lang="en", slow=False).save(str(output_path))
        print("[VOICE] Fallback to gTTS succeeded")
        return output_path
    except Exception as e:
        raise RuntimeError(f"Voice generation failed (edge-tts + gTTS). Last edge error: {last_error}") from e

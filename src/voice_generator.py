import asyncio
import time
from pathlib import Path

import edge_tts
from gtts import gTTS


VOICES = [
    "en-US-GuyNeural",
    "en-US-BrianMultilingualNeural",
    "en-US-AndrewMultilingualNeural",
]


async def _edge_speak(text: str, output_path: Path, voice: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate="+6%")
    await communicate.save(str(output_path))


def generate_voiceover(script: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt, voice in enumerate(VOICES, start=1):
        try:
            asyncio.run(_edge_speak(script, output_path, voice=voice))
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

    return output_path

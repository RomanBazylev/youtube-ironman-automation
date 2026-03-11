import asyncio
import subprocess
import time
from pathlib import Path

import edge_tts
from gtts import gTTS


VOICE_PROFILES = [
    {"voice": "en-US-BrianMultilingualNeural", "rate": "+12%", "pitch": "-8Hz"},
    {"voice": "en-US-AndrewMultilingualNeural", "rate": "+12%", "pitch": "-8Hz"},
    {"voice": "en-US-GuyNeural", "rate": "+10%", "pitch": "-8Hz"},
    {"voice": "en-GB-RyanNeural", "rate": "+10%", "pitch": "-8Hz"},
]


async def _edge_speak(text: str, output_path: Path, voice: str, rate: str, pitch: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))


def _masculinize_and_speedup(output_path: Path) -> None:
    tuned = output_path.with_name(output_path.stem + "_tuned" + output_path.suffix)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(output_path),
            "-af",
            "asetrate=44100*0.90,aresample=44100,atempo=1.28,loudnorm=I=-16:LRA=11:TP=-1.5",
            str(tuned),
        ],
        check=True,
    )
    tuned.replace(output_path)


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
            _masculinize_and_speedup(output_path)
            return output_path
        except Exception as e:
            last_error = e
            print(f"[VOICE] edge-tts attempt {attempt} failed: {e}")
            time.sleep(attempt)

    # Fallback keeps pipeline alive if edge-tts is blocked (e.g., 403 handshake).
    try:
        gTTS(text=script, lang="en", slow=False).save(str(output_path))
        _masculinize_and_speedup(output_path)
        print("[VOICE] Fallback to gTTS succeeded")
        return output_path
    except Exception as e:
        raise RuntimeError(f"Voice generation failed (edge-tts + gTTS). Last edge error: {last_error}") from e

    return output_path

import asyncio
from pathlib import Path

import edge_tts


VOICE = "en-US-GuyNeural"


async def _edge_speak(text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=VOICE, rate="+6%")
    await communicate.save(str(output_path))


def generate_voiceover(script: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_edge_speak(script, output_path))
    return output_path

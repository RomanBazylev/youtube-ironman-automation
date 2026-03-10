from typing import Dict, List


def generate_captions(scenes: List[Dict[str, str | int]]) -> List[str]:
    captions = []
    for scene in scenes:
        cap = str(scene.get("caption_text", "")).strip()
        if not cap:
            cap = "STAY HARD"
        captions.append(cap)
    return captions

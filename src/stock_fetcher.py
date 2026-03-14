import random
import re
import time
from pathlib import Path
from typing import Dict, List

import requests

from config.settings import PEXELS_API_KEY, PIXABAY_API_KEY


BLACKLIST_TERMS = {
    "woman",
    "women",
    "female",
    "girl",
    "girls",
    "lady",
    "ladies",
    "makeup",
    "beauty",
    "skincare",
    "lipstick",
    "nails",
    "cosmetics",
    "salon",
    "manicure",
    "fashion model",
}
MALE_PRIORITY_TERMS = {"man", "male", "men", "masculine", "gentleman", "businessman"}


def _normalize_query(text: str) -> str:
    q = re.sub(r"[^a-zA-Z0-9 ]", " ", text).strip().lower()
    q = re.sub(r"\s+", " ", q)
    return q


def _male_query_variants(base_query: str) -> List[str]:
    base = _normalize_query(base_query)
    if not base:
        base = "discipline"

    variants = [
        f"{base} man",
        f"male {base}",
        f"men {base}",
        base,
    ]

    # Keep order, remove duplicates.
    seen: set[str] = set()
    deduped: List[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


def _contains_blacklist(text: str) -> bool:
    t = _normalize_query(text)
    return any(term in t for term in BLACKLIST_TERMS)


def _male_priority_score(text: str) -> int:
    t = _normalize_query(text)
    return sum(1 for term in MALE_PRIORITY_TERMS if term in t)


def _search_pexels(query: str, per_page: int = 10, orientation: str = "portrait") -> List[Dict]:
    if not PEXELS_API_KEY:
        return []
    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": query,
                "per_page": per_page,
                "orientation": orientation,
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[STOCK] Pexels request failed for '{query}': {e}")
        return []
    videos = response.json().get("videos", [])
    normalized: List[Dict] = []
    for v in videos:
        link = _pick_pexels_file(v)
        if not link:
            continue
        normalized.append(
            {
                "provider": "pexels",
                "id": f"pexels_{v.get('id')}",
                "url": link,
                "searchable_text": " ".join(
                    [
                        str(v.get("url", "")),
                        str(v.get("id", "")),
                        str(v.get("user", {}).get("name", "")),
                        query,
                    ]
                ),
            }
        )
    return normalized


def _pick_pexels_file(video: Dict) -> str | None:
    files = video.get("video_files", [])
    if not files:
        return None
    # Prefer higher quality mp4 assets for cleaner output.
    files = sorted(files, key=lambda f: f.get("width", 0), reverse=True)
    for f in files:
        if f.get("file_type") == "video/mp4":
            return f.get("link")
    return files[0].get("link")


def _search_pixabay(query: str, per_page: int = 10, orientation: str = "portrait") -> List[Dict]:
    if not PIXABAY_API_KEY:
        return []
    try:
        response = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "per_page": per_page,
                "safesearch": "true",
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        safe_msg = str(e)
        if PIXABAY_API_KEY:
            safe_msg = safe_msg.replace(PIXABAY_API_KEY, "***")
        print(f"[STOCK] Pixabay request failed for '{query}': {safe_msg}")
        return []
    hits = response.json().get("hits", [])

    normalized: List[Dict] = []
    for hit in hits:
        video_variants = hit.get("videos", {})
        candidates = [
            video_variants.get("large"),
            video_variants.get("medium"),
            video_variants.get("small"),
            video_variants.get("tiny"),
        ]
        selected = None
        for file_obj in candidates:
            if not file_obj:
                continue

            width = int(file_obj.get("width", 0) or 0)
            height = int(file_obj.get("height", 0) or 0)
            if orientation == "portrait" and width >= height:
                continue
            if orientation == "landscape" and height > width:
                continue

            selected = file_obj
            break

        if not selected:
            continue

        url = selected.get("url")
        if not url:
            continue

        normalized.append(
            {
                "provider": "pixabay",
                "id": f"pixabay_{hit.get('id')}",
                "url": url,
                "searchable_text": " ".join(
                    [
                        str(hit.get("tags", "")),
                        str(hit.get("id", "")),
                        query,
                    ]
                ),
            }
        )
    return normalized


def search_videos(query: str, per_page: int = 10, orientation: str = "portrait") -> List[Dict]:
    pexels = _search_pexels(query=query, per_page=per_page, orientation=orientation)
    pixabay = _search_pixabay(query=query, per_page=per_page, orientation=orientation)
    combined = [item for item in (pexels + pixabay) if not _contains_blacklist(str(item.get("searchable_text", "")))]
    combined.sort(key=lambda item: _male_priority_score(str(item.get("searchable_text", ""))), reverse=True)
    top = combined[: max(1, len(combined) // 2)]
    random.shuffle(top)
    combined = top + combined[len(top):]
    return combined


def download_video(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            if output_path.exists():
                output_path.unlink()
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with output_path.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            if output_path.exists() and output_path.stat().st_size > 1024:
                return output_path
            raise RuntimeError("Downloaded clip is empty or too small")
        except Exception as e:
            last_error = e
            print(f"[STOCK] Download attempt {attempt} failed: {e}")
            time.sleep(attempt)
    raise RuntimeError(f"Failed to download clip after retries: {last_error}")


def download_clips_for_scenes(
    scenes: List[Dict[str, str | int]],
    output_dir: Path,
    video_type: str,
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    orientation = "portrait" if video_type == "short" else "landscape"

    clips: List[Path] = []
    used_urls: set[str] = set()
    for i, scene in enumerate(scenes, start=1):
        query = str(scene["visual_keyword"])
        queries = []
        queries.extend(_male_query_variants(query))
        queries.extend(
            [
                "man discipline",
                "man mental toughness",
                "male self improvement",
                "man making decision",
                "man leadership",
                "stoic man",
                "man training gym",
            ]
        )
        result: List[Dict] = []
        for q in queries:
            result = search_videos(query=q, per_page=12, orientation=orientation)
            if result:
                break
        if not result:
            raise RuntimeError("No clips returned from Pexels/Pixabay")

        random.shuffle(result)
        picked = None
        for item in result:
            candidate = item.get("url")
            if candidate and candidate not in used_urls:
                picked = candidate
                used_urls.add(candidate)
                break
        if not picked and result:
            picked = result[0].get("url")
        if not picked:
            raise RuntimeError(f"No downloadable file for scene {i}")

        path = output_dir / f"clip_{i:02d}.mp4"
        download_video(picked, path)
        clips.append(path)
    return clips

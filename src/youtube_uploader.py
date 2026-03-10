import time
from pathlib import Path
from typing import List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config.settings import (
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REFRESH_TOKEN,
)


def _youtube_client():
    if not all([YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN]):
        raise RuntimeError("YouTube credentials are not fully configured")

    creds = Credentials(
        None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    category_id: str = "27",
    privacy_status: str = "public",
) -> str:
    youtube = _youtube_client()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:15],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = None
            while response is None:
                _, response = request.next_chunk()
            return response["id"]
        except Exception as e:
            last_error = e
            print(f"[YOUTUBE] Upload attempt {attempt} failed: {e}")
            time.sleep(attempt * 3)

    raise RuntimeError(f"YouTube upload failed after retries: {last_error}")


def set_thumbnail(video_id: str, thumbnail_path: Path) -> None:
    youtube = _youtube_client()
    media = MediaFileUpload(str(thumbnail_path))
    for attempt in range(1, 4):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
            return
        except Exception as e:
            print(f"[YOUTUBE] Thumbnail attempt {attempt} failed: {e}")
            time.sleep(attempt * 2)
    raise RuntimeError("Failed to set thumbnail after retries")


def publish_video(video_id: str, privacy_status: str = "public") -> None:
    youtube = _youtube_client()
    for attempt in range(1, 4):
        try:
            youtube.videos().update(
                part="status",
                body={"id": video_id, "status": {"privacyStatus": privacy_status}},
            ).execute()
            return
        except Exception as e:
            print(f"[YOUTUBE] Publish attempt {attempt} failed: {e}")
            time.sleep(attempt * 2)
    raise RuntimeError("Failed to update publish status after retries")

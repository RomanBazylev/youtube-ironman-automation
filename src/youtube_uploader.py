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

    response = None
    while response is None:
        _, response = request.next_chunk()

    return response["id"]


def set_thumbnail(video_id: str, thumbnail_path: Path) -> None:
    youtube = _youtube_client()
    media = MediaFileUpload(str(thumbnail_path))
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


def publish_video(video_id: str) -> None:
    youtube = _youtube_client()
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": {"privacyStatus": "public"}},
    ).execute()

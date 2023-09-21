from typing import Optional
from googleapiclient.discovery import build
import re
import isodate

YOUTUBE_URL_PATTERNS = [
    r"^https?://(?:www\.)?youtube\.com/watch\?v=([\w-]+)",
    r"^https?://(?:www\.)?youtube\.com/embed/([\w-]+)",
    r"^https?://youtu\.be/([\w-]+)",
]

def _extract_video_id(yt_link) -> Optional[str]:
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, yt_link)
        if match:
            return match.group(1)

    # return None if no match is found
    return None

def get_video_duration(yt_video_link):
    video_id = _extract_video_id(yt_video_link)
    youtube = build('youtube', 'v3', developerKey="AIzaSyAVDA1p-V-yiyQcAC84mdURZnd6EMFeH6k")
    request = youtube.videos().list(part='contentDetails', id=video_id)
    response = request.execute()

    dur = isodate.parse_duration(response['items'][0]['contentDetails']['duration'])
    return dur.total_seconds()
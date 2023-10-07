from typing import Optional
import re

YOUTUBE_URL_PATTERNS = [
    r"^https?://(?:www\.)?youtube\.com/watch\?v=([\w-]+)",
    r"^https?://(?:www\.)?youtube\.com/embed/([\w-]+)",
    r"^https?://youtu\.be/([\w-]+)",
]

def extract_video_id(yt_link) -> Optional[str]:
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, yt_link)
        if match:
            return match.group(1)

    # return None if no match is found
    return None
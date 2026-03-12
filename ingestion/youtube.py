import hashlib
from datetime import datetime

import feedparser

import db


def _make_external_id(video_id):
    return f"yt_{video_id}"


def fetch_youtube(source):
    """Fetch videos from a YouTube channel RSS feed. Returns count of new items."""
    url = source["url"]
    # YouTube RSS feed format: https://www.youtube.com/feeds/videos.xml?channel_id=XXXXX
    # If user provided a channel URL, try to convert
    if "channel_id=" not in url and "/feeds/videos.xml" not in url:
        # Assume the url IS the channel ID
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={url}"

    feed = feedparser.parse(url)
    count = 0

    for entry in feed.entries:
        video_url = entry.get("link", "")
        if not video_url:
            continue

        # Extract video ID from yt:videoId tag or URL
        video_id = entry.get("yt_videoid", "")
        if not video_id and "v=" in video_url:
            video_id = video_url.split("v=")[-1].split("&")[0]
        if not video_id:
            video_id = hashlib.sha256(video_url.encode()).hexdigest()[:16]

        title = entry.get("title", "Untitled")
        # YouTube RSS includes media:description
        summary = ""
        if hasattr(entry, "media_group") and entry.media_group:
            for mg in entry.media_group:
                if hasattr(mg, "media_description"):
                    summary = mg.media_description
                    break
        if not summary:
            summary = entry.get("summary", "")

        if summary and len(summary) > 500:
            summary = summary[:500] + "..."

        author = entry.get("author", source["name"])
        published = None
        if entry.get("published_parsed"):
            try:
                published = datetime(*entry.published_parsed[:6]).isoformat()
            except (TypeError, ValueError):
                pass
        if not published:
            published = datetime.utcnow().isoformat()

        db.save_item(
            source_id=source["id"],
            external_id=_make_external_id(video_id),
            title=title,
            author=author,
            summary=summary,
            url=video_url,
            source_type="youtube",
            published_at=published,
        )
        count += 1

    return count


def ingest_all_youtube():
    """Fetch all active YouTube sources. Returns total new items."""
    sources = db.get_active_sources()
    total = 0
    for source in sources:
        if source["type"] == "youtube_channel":
            try:
                n = fetch_youtube(source)
                total += n
                print(f"  YouTube [{source['name']}]: {n} items")
            except Exception as e:
                print(f"  YouTube [{source['name']}] ERROR: {e}")
    return total

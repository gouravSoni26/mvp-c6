import hashlib
from datetime import datetime, timedelta
import time

import feedparser

import db


def _make_external_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _parse_date(entry):
    """Extract published date from feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6]).isoformat()
            except (TypeError, ValueError):
                pass
    return datetime.utcnow().isoformat()


def fetch_rss(source):
    """Fetch items from an RSS feed source. Returns count of new items."""
    feed = feedparser.parse(source["url"])
    cutoff = datetime.utcnow() - timedelta(hours=48)
    count = 0

    for entry in feed.entries:
        url = entry.get("link", "")
        if not url:
            continue

        title = entry.get("title", "Untitled")
        summary = entry.get("summary", entry.get("description", ""))
        # Strip HTML tags from summary (basic)
        if summary:
            import re
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            if len(summary) > 500:
                summary = summary[:500] + "..."

        author = entry.get("author", source["name"])
        published = _parse_date(entry)

        external_id = _make_external_id(url)

        db.save_item(
            source_id=source["id"],
            external_id=external_id,
            title=title,
            author=author,
            summary=summary,
            url=url,
            source_type="newsletter",
            published_at=published,
        )
        count += 1

    return count


def ingest_all_rss():
    """Fetch all active RSS sources. Returns total new items."""
    sources = db.get_active_sources()
    total = 0
    for source in sources:
        if source["type"] == "rss":
            try:
                n = fetch_rss(source)
                total += n
                print(f"  RSS [{source['name']}]: {n} items")
            except Exception as e:
                print(f"  RSS [{source['name']}] ERROR: {e}")
    return total

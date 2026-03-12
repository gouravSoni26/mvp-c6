from apify_client import ApifyClient

import db
import config

ACTOR_ID = "apidojo/tweet-scraper"


def _get_apify_client():
    return ApifyClient(config.APIFY_API_TOKEN)


def _parse_tweet(tweet, source):
    """Extract fields from an apidojo/tweet-scraper dataset item."""
    tweet_id = tweet.get("id") or tweet.get("id_str") or ""
    text = tweet.get("full_text") or tweet.get("text") or ""
    created_at = tweet.get("createdAt") or tweet.get("created_at") or ""

    # Author can be a nested object or flat fields
    author_obj = tweet.get("author") or {}
    if isinstance(author_obj, dict):
        author = "@" + author_obj.get("userName", author_obj.get("username", "unknown"))
    else:
        author = "@" + (tweet.get("user", {}).get("screen_name") or "unknown")

    tweet_url = tweet.get("url") or f"https://x.com/i/status/{tweet_id}"
    title = text[:100] + ("..." if len(text) > 100 else "")

    return {
        "source_id": source["id"],
        "external_id": f"tw_{tweet_id}",
        "title": title,
        "author": author,
        "summary": text,
        "url": tweet_url,
        "source_type": "twitter",
        "published_at": created_at or None,
    }


def fetch_twitter_source(source):
    """Fetch tweets from the latest scheduled Apify run for a source. Returns count of new items."""
    if not config.APIFY_API_TOKEN:
        print(f"  Twitter [{source['name']}]: Skipped (no APIFY_API_TOKEN)")
        return 0

    client = _get_apify_client()

    # source["url"] holds the handle or search query used as the actor's input
    # We look up the latest successful run of the actor and read its dataset
    actor_client = client.actor(ACTOR_ID)
    runs = actor_client.runs().list(limit=1, desc=True, status="SUCCEEDED")

    if not runs.items:
        print(f"  Twitter [{source['name']}]: No successful runs found for {ACTOR_ID}")
        return 0

    latest_run = runs.items[0]
    dataset_id = latest_run.get("defaultDatasetId")
    if not dataset_id:
        print(f"  Twitter [{source['name']}]: No dataset in latest run")
        return 0

    dataset = client.dataset(dataset_id)
    items = dataset.list_items().items

    if not items:
        print(f"  Twitter [{source['name']}]: Dataset empty")
        return 0

    # Filter tweets relevant to this source's handle/query
    search_term = source["url"].lower().lstrip("@")
    count = 0
    for tweet in items:
        # Match by author handle or presence of search term in text
        author_obj = tweet.get("author") or {}
        author_handle = ""
        if isinstance(author_obj, dict):
            author_handle = (author_obj.get("userName") or author_obj.get("username") or "").lower()
        else:
            author_handle = (tweet.get("user", {}).get("screen_name") or "").lower()

        text = (tweet.get("full_text") or tweet.get("text") or "").lower()

        if search_term in author_handle or search_term in text:
            parsed = _parse_tweet(tweet, source)
            db.save_item(**parsed)
            count += 1

    print(f"  Twitter [{source['name']}]: {count} items from latest Apify run")
    return count


def ingest_all_twitter():
    """Fetch all active Twitter sources via Apify. Returns total new items."""
    sources = db.get_active_sources()
    total = 0
    for source in sources:
        if source["type"] == "twitter_list":
            try:
                n = fetch_twitter_source(source)
                total += n
            except Exception as e:
                print(f"  Twitter [{source['name']}] ERROR: {e}")
    return total

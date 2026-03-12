import json
from datetime import date

from openai import OpenAI

import db
import config


def build_digest(target_date=None):
    """Build digest data structure from top-scored items.

    Returns dict with:
        - must_reads: top 3 items (for top_3 format)
        - remaining: items 4-15
        - by_source: items grouped by source_type (for grouped format)
        - by_theme: items grouped by AI-detected theme (for themed format)
        - date: digest date string
        - total: total items
        - precision_alert: True if precision <60% for 3 days
    """
    if target_date is None:
        target_date = date.today().isoformat()

    items = db.get_top_items(target_date, limit=15)

    if not items:
        return {
            "must_reads": [],
            "remaining": [],
            "by_source": {},
            "by_theme": {},
            "date": target_date,
            "total": 0,
            "precision_alert": False,
        }

    # Mark items as included in digest
    db.mark_items_in_digest([item["id"] for item in items], target_date)

    # Top 3 must-reads
    must_reads = items[:3]
    remaining = items[3:]

    # Group by source
    by_source = {}
    for item in items:
        src = item.get("source_type", "other")
        label = {"twitter": "Twitter", "newsletter": "Newsletters", "youtube": "YouTube"}.get(src, "Other")
        by_source.setdefault(label, []).append(item)

    # Group by theme (AI-detected)
    by_theme = _detect_themes(items)

    # Check precision alert
    daily_precision = db.get_daily_precision(days=3)
    precision_alert = (
        len(daily_precision) >= 3
        and all(p is not None and p < 0.6 for _, p in daily_precision)
    )

    return {
        "must_reads": must_reads,
        "remaining": remaining,
        "by_source": by_source,
        "by_theme": by_theme,
        "date": target_date,
        "total": len(items),
        "precision_alert": precision_alert,
    }


def _detect_themes(items):
    """Use GPT-4o to group items into themes. Falls back to source-based grouping."""
    if not items or not config.OPENAI_API_KEY:
        return {"General": items}

    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        items_text = "\n".join(
            f"ID {item['id']}: {item['title']}" for item in items
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"""Group these content items into 2-5 thematic categories.
Return a JSON object where keys are short theme names and values are arrays of item IDs.

Items:
{items_text}

Example output: {{"Agent Tools": [1, 3], "LLM Theory": [2, 5], "Production Patterns": [4]}}
Return ONLY the JSON object.""",
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        themes_map = json.loads(response.choices[0].message.content)
        # Convert ID lists to item lists
        items_by_id = {item["id"]: item for item in items}
        result = {}
        for theme, ids in themes_map.items():
            theme_items = [items_by_id[i] for i in ids if i in items_by_id]
            if theme_items:
                result[theme] = theme_items
        return result if result else {"General": items}
    except Exception as e:
        print(f"  Theme detection failed: {e}")
        return {"General": items}


def generate_subject_line(must_reads, total):
    """Generate a personalized subject line for the digest email."""
    if not must_reads:
        return "Your Daily AI Learning Digest"

    # Find the most relevant topic from top item
    top_title = must_reads[0].get("title", "")
    # Extract a short topic keyword
    remaining_count = total - len(must_reads)

    if len(must_reads) >= 3:
        return f"3 Must-Reads: {top_title[:40]}... + {remaining_count} More"
    return f"Your Daily AI Learning Digest — {total} Items Curated"

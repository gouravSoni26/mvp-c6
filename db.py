from datetime import date

from supabase import create_client

import config

_client = None


def get_client():
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client


def init_db():
    sb = get_client()
    row = sb.table("learning_context").select("id").eq("id", 1).execute()
    if not row.data:
        sb.table("learning_context").insert({"id": 1}).execute()


# --- Learning Context ---

def get_context():
    sb = get_client()
    row = sb.table("learning_context").select("*").eq("id", 1).maybe_single().execute()
    if row.data is None:
        return {}
    return row.data


def save_context(data):
    sb = get_client()
    sb.table("learning_context").update({
        "learning_goals": data.get("learning_goals", ""),
        "digest_format": data.get("digest_format", "top_3"),
        "learning_style": data.get("learning_style", "build_first"),
        "depth_preference": data.get("depth_preference", "mixed_with_flags"),
        "consumption_habits": data.get("consumption_habits", "mixed"),
        "skill_levels": data.get("skill_levels", {}),
        "time_availability": data.get("time_availability", "30 mins/day"),
        "project_context": data.get("project_context", ""),
    }).eq("id", 1).execute()


# --- Sources ---

def get_active_sources():
    sb = get_client()
    resp = sb.table("sources").select("*").eq("active", True).execute()
    return resp.data


def get_all_sources():
    sb = get_client()
    resp = sb.table("sources").select("*").order("created_at", desc=True).execute()
    return resp.data


def add_source(type_, name, url):
    sb = get_client()
    sb.table("sources").insert({
        "type": type_,
        "name": name,
        "url": url,
    }).execute()


def delete_source(source_id):
    sb = get_client()
    sb.table("sources").delete().eq("id", source_id).execute()


# --- Items ---

def save_item(source_id, external_id, title, author, summary, url, source_type, published_at):
    sb = get_client()
    sb.table("items").upsert({
        "source_id": source_id,
        "external_id": external_id,
        "title": title,
        "author": author,
        "summary": summary,
        "url": url,
        "source_type": source_type,
        "published_at": published_at,
    }, on_conflict="external_id", ignore_duplicates=True).execute()


def get_unscored_items():
    sb = get_client()
    resp = sb.table("items").select("*").is_("relevance_score", "null").order("published_at", desc=True).execute()
    return resp.data


def save_score(item_id, score, justification):
    sb = get_client()
    sb.table("items").update({
        "relevance_score": score,
        "score_justification": justification,
    }).eq("id", item_id).execute()


def get_top_items(target_date=None, limit=15):
    if target_date is None:
        target_date = date.today().isoformat()
    sb = get_client()
    resp = (
        sb.table("items")
        .select("*")
        .not_.is_("relevance_score", "null")
        .or_(f"digest_date.is.null,digest_date.eq.{target_date}")
        .order("relevance_score", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data


def mark_items_in_digest(item_ids, target_date=None):
    if target_date is None:
        target_date = date.today().isoformat()
    sb = get_client()
    sb.table("items").update({
        "included_in_digest": True,
        "digest_date": target_date,
    }).in_("id", item_ids).execute()


# --- Feedback ---

def log_feedback(item_id, rating):
    sb = get_client()
    sb.table("feedback").insert({
        "item_id": item_id,
        "rating": rating,
    }).execute()


def get_precision(days=7):
    sb = get_client()
    resp = sb.rpc("get_precision", {"num_days": days}).execute()
    if not resp.data:
        return None
    row = resp.data[0]
    if row["total"] == 0:
        return None
    return row["useful"] / row["total"]


def get_daily_precision(days=3):
    """Get precision for each of the last N days. Returns list of (date, precision)."""
    sb = get_client()
    resp = sb.rpc("get_daily_precision", {"num_days": days}).execute()
    return [
        (r["day"], r["useful"] / r["total"] if r["total"] > 0 else None)
        for r in resp.data
    ]


if __name__ == "__main__":
    init_db()
    print("Database initialized (Supabase)")
    ctx = get_context()
    print(f"Learning context: {ctx}")

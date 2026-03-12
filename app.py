import json
from flask import Flask, render_template, request, redirect, url_for, flash

import db
import config

app = Flask(__name__)
app.secret_key = "feed-curator-mvp-secret"


@app.before_request
def ensure_db():
    db.init_db()


# --- Learning Context ---

@app.route("/")
def index():
    ctx = db.get_context()
    # Convert skill_levels dict to editable text
    if isinstance(ctx.get("skill_levels"), dict):
        ctx["skill_levels_text"] = "\n".join(
            f"{k}: {v}" for k, v in ctx["skill_levels"].items()
        )
    else:
        ctx["skill_levels_text"] = ""
    precision = db.get_precision(days=7)
    return render_template("context_form.html", ctx=ctx, precision=precision)


@app.route("/context", methods=["POST"])
def save_context():
    # Parse skill_levels from textarea (format: "Skill: Level\nSkill: Level")
    skill_text = request.form.get("skill_levels_text", "")
    skill_levels = {}
    for line in skill_text.strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            skill_levels[key.strip()] = val.strip()

    data = {
        "learning_goals": request.form.get("learning_goals", ""),
        "digest_format": request.form.get("digest_format", "top_3"),
        "learning_style": request.form.get("learning_style", "build_first"),
        "depth_preference": request.form.get("depth_preference", "mixed_with_flags"),
        "consumption_habits": request.form.get("consumption_habits", "mixed"),
        "skill_levels": skill_levels,
        "time_availability": request.form.get("time_availability", "30 mins/day"),
        "project_context": request.form.get("project_context", ""),
    }
    db.save_context(data)
    flash("Learning Context saved successfully!", "success")
    return redirect(url_for("index"))


# --- Feedback ---

@app.route("/feedback/<int:item_id>/<rating>")
def feedback(item_id, rating):
    if rating not in ("useful", "not_useful"):
        return "Invalid rating", 400
    db.log_feedback(item_id, rating)
    return render_template("feedback.html", rating=rating)


# --- Sources ---

@app.route("/sources")
def sources():
    all_sources = db.get_all_sources()
    return render_template("sources.html", sources=all_sources)


@app.route("/sources", methods=["POST"])
def add_source():
    type_ = request.form.get("type", "rss")
    name = request.form.get("name", "")
    url = request.form.get("url", "")
    if name and url:
        db.add_source(type_, name, url)
        flash(f"Source '{name}' added!", "success")
    else:
        flash("Name and URL are required.", "error")
    return redirect(url_for("sources"))


@app.route("/sources/<int:source_id>/delete", methods=["POST"])
def delete_source(source_id):
    db.delete_source(source_id)
    flash("Source removed.", "success")
    return redirect(url_for("sources"))


# --- Digest Preview ---

@app.route("/digest/preview")
def digest_preview():
    from digest.builder import build_digest
    ctx = db.get_context()
    digest_data = build_digest()
    fmt = ctx.get("digest_format", "top_3")
    template_map = {
        "top_3": "email/top3.html",
        "grouped_by_source": "email/grouped.html",
        "themed_by_topic": "email/themed.html",
    }
    template = template_map.get(fmt, "email/top3.html")
    return render_template(template, digest=digest_data, ctx=ctx, base_url=config.APP_BASE_URL)


@app.route("/digest/send", methods=["POST"])
def send_digest():
    from digest.builder import build_digest
    from digest.emailer import send_digest_email
    digest_data = build_digest()
    ctx = db.get_context()
    try:
        send_digest_email(digest_data, ctx)
        flash("Digest sent!", "success")
    except Exception as e:
        flash(f"Failed to send digest: {e}", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host=config.APP_HOST, port=config.APP_PORT, debug=True)

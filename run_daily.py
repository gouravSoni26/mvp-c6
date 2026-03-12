#!/usr/bin/env python3
"""Daily pipeline: ingest → score → build → send digest.

Usage:
    python run_daily.py              # Run full pipeline
    python run_daily.py --dry-run    # Run without sending email
    python run_daily.py --ingest     # Only run ingestion
    python run_daily.py --score      # Only run scoring
    python run_daily.py --send       # Only build + send digest
"""

import sys
import logging
from datetime import datetime

import db
from ingestion.rss import ingest_all_rss
from ingestion.youtube import ingest_all_youtube
from ingestion.twitter import ingest_all_twitter
from scoring.scorer import score_unscored
from digest.builder import build_digest
from digest.emailer import send_digest_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run_ingestion():
    """Ingest content from all sources. Returns total items fetched."""
    log.info("=== Ingestion ===")
    total = 0
    errors = []

    for name, fn in [("RSS", ingest_all_rss), ("YouTube", ingest_all_youtube), ("Twitter", ingest_all_twitter)]:
        try:
            n = fn()
            total += n
            log.info(f"{name}: {n} items ingested")
        except Exception as e:
            log.error(f"{name} ingestion failed: {e}")
            errors.append(name)

    log.info(f"Ingestion complete: {total} total items ({len(errors)} source errors)")
    return total, errors


def run_scoring():
    """Score all unscored items."""
    log.info("=== Scoring ===")
    try:
        score_unscored()
        log.info("Scoring complete")
        return True
    except Exception as e:
        log.error(f"Scoring failed: {e}")
        return False


def run_digest(dry_run=False, ingestion_errors=None):
    """Build and optionally send the digest email."""
    log.info("=== Digest ===")
    try:
        digest_data = build_digest()
    except Exception as e:
        log.error(f"Digest build failed: {e}")
        return False

    total = digest_data.get("total", 0)
    if total == 0:
        log.warning("No items to include in digest. Skipping send.")
        return True

    log.info(f"Digest built: {total} items (top 3: {[i['title'][:50] for i in digest_data.get('must_reads', [])]})")

    # Add footnote about errors if any sources failed
    if ingestion_errors:
        footnote = f"Note: Some sources had errors during ingestion ({', '.join(ingestion_errors)}). This digest may be incomplete."
        digest_data["footnote"] = footnote
        log.warning(footnote)

    if dry_run:
        log.info("Dry run — skipping email send")
        log.info(f"Would send digest with {total} items")
        return True

    ctx = db.get_context()
    try:
        send_digest_email(digest_data, ctx)
        log.info("Digest email sent successfully")
        return True
    except Exception as e:
        log.error(f"Email send failed: {e}")
        return False


def run_full_pipeline(dry_run=False):
    """Run the complete daily pipeline."""
    start = datetime.now()
    log.info(f"Starting daily pipeline at {start.isoformat()}")

    # Step 0: Ensure DB is initialized
    db.init_db()

    # Step 1: Ingest
    total_items, ingestion_errors = run_ingestion()

    # Step 2: Score
    scoring_ok = run_scoring()
    if not scoring_ok:
        log.warning("Scoring failed — will attempt digest with previously scored items")

    # Step 3: Build + Send
    run_digest(dry_run=dry_run, ingestion_errors=ingestion_errors)

    elapsed = (datetime.now() - start).total_seconds()
    log.info(f"Pipeline complete in {elapsed:.1f}s")


if __name__ == "__main__":
    args = set(sys.argv[1:])

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    dry_run = "--dry-run" in args

    # Ensure DB is ready for any mode
    db.init_db()

    if "--ingest" in args:
        run_ingestion()
    elif "--score" in args:
        run_scoring()
    elif "--send" in args:
        run_digest(dry_run=dry_run)
    else:
        run_full_pipeline(dry_run=dry_run)

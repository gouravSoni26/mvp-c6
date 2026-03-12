# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plan & Review

### Before starting work
- Always enter plan mode to make a plan first.
- Write the plan to `.claude/tasks/TASK_NAME.md`.
- The plan should be a detailed implementation plan with reasoning and broken-down tasks.
- If the task requires external knowledge or a certain package, research to get latest knowledge (use Task tool).
- Don't over-plan — always think MVP.
- Once the plan is written, ask for review first. Do not continue until the plan is approved.

### While implementing
- Update the plan as you work.
- After completing tasks in the plan, append detailed descriptions of changes made so following tasks can be handed over to other engineers.

## Build & Run

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env   # then fill in API keys
python db.py            # verify Supabase connection & ensure default row exists

# Run web UI
python app.py           # Flask on http://localhost:5000

# Run daily pipeline
python run_daily.py              # full pipeline: ingest → score → send
python run_daily.py --dry-run    # skip email send
python run_daily.py --ingest     # ingestion only
python run_daily.py --score      # scoring only
python run_daily.py --send       # build + send digest only

# Cron (daily at 7am)
# 0 7 * * * cd /path/to/mvp-c6 && python run_daily.py >> data/pipeline.log 2>&1
```

## Architecture

Single-user AI content curator: ingests RSS/YouTube/Twitter → scores with GPT-4o → sends daily email digest via Resend.

- `app.py` — Flask web UI for managing Learning Context, sources, and previewing digests
- `run_daily.py` — CLI pipeline orchestrator (cron entry point)
- `db.py` + `schema.sql` — Supabase (PostgreSQL) data layer (4 tables: learning_context, sources, items, feedback)
- `ingestion/` — Content fetchers (rss.py, youtube.py, twitter.py)
- `scoring/scorer.py` — Batched GPT-4o relevance scoring against Learning Context
- `digest/builder.py` — Selects top items, groups by source/theme
- `digest/emailer.py` — Renders Jinja2 email templates, sends via Resend
- `templates/email/` — 3 digest formats: top3, grouped, themed

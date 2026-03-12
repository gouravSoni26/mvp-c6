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

# Run the full pipeline
python -m src.pipeline

# Start the feedback API
uvicorn src.feedback.api:app --reload

# Start the Streamlit UI
streamlit run streamlit_app/app.py

# Run tests
python -m pytest tests/ -v
```

## Architecture

Single-user AI content curator: ingests RSS/YouTube/Twitter → scores with GPT-4o → sends daily email digest via Resend.

- `src/config.py` — Pydantic settings, env vars, budget limits
- `src/models.py` — ContentItem, ScoredItem, LearningContext, CostTracker
- `src/db.py` — Supabase CRUD helpers
- `src/pipeline.py` — Main daily orchestrator with budget gates
- `src/ingestion/` — Content fetchers (newsletters.py, youtube.py, twitter.py)
- `src/scoring/scorer.py` — Batched GPT-4o relevance scoring (12 items/batch)
- `src/digest/builder.py` — Selects top items, builds HTML email
- `src/delivery/emailer.py` — Sends digest + alert emails via Resend
- `src/feedback/api.py` — FastAPI: /feedback, /health, /stats, /trigger
- `src/monitoring/precision.py` — Precision tracking + low-precision alerts
- `streamlit_app/app.py` — Learning Context web form
- `scripts/` — DB init SQL, migration, seed script
- `tests/` — pytest test suite
- `.github/workflows/daily_digest.yml` — Daily cron (6 AM UTC) + manual trigger

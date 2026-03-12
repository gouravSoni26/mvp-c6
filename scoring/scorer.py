import json

from openai import OpenAI

import config
import db

SCORING_PROMPT = """You are a personalized learning content curator. Score each content item's relevance for a user based on their Learning Context.

**Learning Context:**
- Goals: {learning_goals}
- Skill Levels: {skill_levels}
- Project Context: {project_context}
- Learning Style: {learning_style}
- Depth Preference: {depth_preference}
- Consumption Habits: {consumption_habits}
- Time Availability: {time_availability}

**Scoring Criteria (weighted):**
- Relevance to current learning goals and project context (50%)
- Alignment with skill level — not too basic, not too advanced (20%)
- Match with learning style and depth preference (20%)
- Actionability — can the user apply this to their project? (10%)

**Content Items to Score:**
{items_text}

**Instructions:**
1. Score each item from 0 to 10 (integer).
2. Provide a 1-sentence justification using "you/your" pronouns, tying the score to the user's goals or project.
3. Do NOT over-filter. Borderline relevant items (score 5-6) should still be included.
4. Do NOT penalize recency unless content is clearly outdated.

**Output Format (JSON array):**
[
  {{"id": 1, "score": 8, "justification": "Explains MCP with code examples, directly applicable to your research agent project."}},
  ...
]

Return ONLY the JSON array, no other text."""


def _format_items(items):
    lines = []
    for item in items:
        lines.append(f"Item ID: {item['id']}")
        lines.append(f"  Title: {item['title']}")
        lines.append(f"  Source: {item.get('source_type', 'unknown')}")
        lines.append(f"  Author: {item.get('author', 'Unknown')}")
        lines.append(f"  Summary: {(item.get('summary') or '')[:300]}")
        lines.append("")
    return "\n".join(lines)


def _format_skill_levels(skill_levels):
    if isinstance(skill_levels, dict):
        return ", ".join(f"{k}: {v}" for k, v in skill_levels.items())
    return str(skill_levels)


def score_items(items, context, batch_size=5):
    """Score a list of items using GPT-4o. Updates DB with scores."""
    if not items:
        return

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        prompt = SCORING_PROMPT.format(
            learning_goals=context.get("learning_goals", "Not specified"),
            skill_levels=_format_skill_levels(context.get("skill_levels", {})),
            project_context=context.get("project_context", "Not specified"),
            learning_style=context.get("learning_style", "build_first"),
            depth_preference=context.get("depth_preference", "mixed_with_flags"),
            consumption_habits=context.get("consumption_habits", "mixed"),
            time_availability=context.get("time_availability", "30 mins/day"),
            items_text=_format_items(batch),
        )

        scores = _call_gpt4o(client, prompt)
        if scores:
            for score_entry in scores:
                item_id = score_entry.get("id")
                score = score_entry.get("score", 0)
                justification = score_entry.get("justification", "")
                # Normalize score to 0.0-1.0 for DB storage
                normalized = max(0.0, min(1.0, score / 10.0))
                db.save_score(item_id, normalized, justification)
                print(f"    Scored item {item_id}: {score}/10 — {justification[:60]}")


def _call_gpt4o(client, prompt, retries=2):
    """Call GPT-4o with retry logic for JSON parsing."""
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            # Handle if model wraps array in an object
            if isinstance(parsed, dict):
                for key in ("items", "scores", "results"):
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                # If it's a single score wrapped in an object
                if "id" in parsed:
                    return [parsed]
            if isinstance(parsed, list):
                return parsed
            return []
        except (json.JSONDecodeError, Exception) as e:
            if attempt < retries:
                print(f"    Scoring retry {attempt + 1}: {e}")
                continue
            print(f"    Scoring failed after {retries + 1} attempts: {e}")
            return []


def score_unscored():
    """Score all unscored items in the database."""
    items = db.get_unscored_items()
    if not items:
        print("  No unscored items found.")
        return
    context = db.get_context()
    print(f"  Scoring {len(items)} items...")
    score_items(items, context)

"""
ai_processor.py
---------------
Two jobs, run right after scraper.py:

1) CATEGORIZE each newly scraped article and write a short AI
   summary onto it (still keeps status = 'Pending Verification'
   until a human approves it in the Admin Dashboard).

2) BUILD roll-up summaries:
   - Daily summary   -> articles scraped in the last 1 day
   - Weekly summary  -> articles scraped in the last 7 days
   - Monthly summary -> articles scraped in the last 30 days
   These are saved to the "summaries" table and are what gets
   emailed to you daily. They are NOT shown on the public website
   (the public site only ever shows individually Approved articles).

Uses Groq's free LLM API (https://console.groq.com) — no credit
card required for the free tier as of this writing. Swap
GROQ_MODEL / the call_llm() function if you'd rather use another
provider (Google Gemini's free tier works the same way).
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, GROQ_API_KEY]):
    print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_KEY / GROQ_API_KEY are missing.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

CATEGORIES = [
    "Economics", "Construction", "Tourism", "Regulation",
    "Political", "Oil Price (Local)", "Oil Price (World)",
]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Call Groq's OpenAI-compatible chat completion endpoint."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------
# STEP 1: categorize + summarize individual pending articles
# ---------------------------------------------------------------
def categorize_and_summarize_articles():
    result = (
        supabase.table("articles")
        .select("*")
        .is_("ai_summary", "null")
        .execute()
    )
    articles = result.data
    print(f"Found {len(articles)} article(s) needing AI categorization/summary.")

    system_prompt = (
        "You are a news analyst for a Cambodian building-materials company. "
        "You always reply with ONLY a valid JSON object, no extra text, no markdown fences. "
        f"The 'category' field MUST be exactly one of: {', '.join(CATEGORIES)}. "
        "The 'region' field MUST be exactly 'Local' (about Cambodia) or 'World' (international)."
    )

    for art in articles:
        text_for_ai = (art.get("raw_text") or "")[:4000] or art["title"]
        user_prompt = (
            f'Title: "{art["title"]}"\n\n'
            f"Article text: {text_for_ai}\n\n"
            "Return JSON with exactly these keys:\n"
            '{"category": "...", "region": "Local or World", '
            '"summary": "a neutral 2-3 sentence summary aimed at a business executive, '
            "focusing on any impact to Cambodia's economy, construction/building-materials "
            'sector, or oil/fuel prices if relevant"}'
        )
        try:
            raw = call_llm(system_prompt, user_prompt)
            raw_clean = raw.strip().strip("`").replace("json\n", "").strip()
            data = json.loads(raw_clean)
            category = data.get("category") if data.get("category") in CATEGORIES else art.get("category")
            region = data.get("region") if data.get("region") in ("Local", "World") else art.get("region")
            summary = data.get("summary", "").strip()

            supabase.table("articles").update({
                "category": category,
                "region": region,
                "ai_summary": summary or "(AI summary unavailable — please write one manually.)",
            }).eq("id", art["id"]).execute()
            print(f"  ✓ Processed: {art['title'][:70]}")
        except Exception as e:
            print(f"  ! AI processing failed for '{art['title'][:60]}': {e}")
            # Fall back so it isn't stuck forever waiting for AI
            supabase.table("articles").update({
                "ai_summary": "(AI summary failed — please review/edit manually.)",
            }).eq("id", art["id"]).execute()


# ---------------------------------------------------------------
# STEP 2: build daily / weekly / monthly roll-up summaries
# ---------------------------------------------------------------
def build_rollup_summary(period_type: str, days_back: int):
    period_end = datetime.now(timezone.utc).date()
    period_start = period_end - timedelta(days=days_back - 1)

    result = (
        supabase.table("articles")
        .select("title, category, region, ai_summary, scraped_at")
        .gte("scraped_at", period_start.isoformat())
        .execute()
    )
    articles = result.data
    if not articles:
        print(f"No articles for {period_type} summary — skipping.")
        return

    bullet_list = "\n".join(
        f"- [{a.get('category')}] {a['title']}: {a.get('ai_summary') or ''}"
        for a in articles
    )

    label = {"daily": "today", "weekly": "the past 7 days", "monthly": "the past 30 days"}[period_type]
    system_prompt = (
        "You are preparing an executive briefing for the leadership team of a cement and "
        "building-materials company in Cambodia (CBM Cambodia). Be concise, business-focused, "
        "and highlight anything with real impact on Cambodia's economy, construction/building "
        "materials demand, regulation, or oil/fuel costs. Use plain text with short paragraphs "
        "or bullet points — no markdown headers."
    )
    user_prompt = (
        f"Here are the news items collected over {label}:\n\n{bullet_list}\n\n"
        f"Write a {'3-5 sentence' if period_type == 'daily' else '1-2 short paragraph'} "
        "executive summary of what matters most from this list."
    )

    try:
        summary_text = call_llm(system_prompt, user_prompt, max_tokens=700)
    except Exception as e:
        print(f"  ! Failed to generate {period_type} summary: {e}")
        summary_text = "(Automatic summary generation failed this run. See raw article list in the admin dashboard.)"

    supabase.table("summaries").upsert({
        "period_type": period_type,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "summary_text": summary_text,
        "article_count": len(articles),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="period_type,period_start").execute()

    print(f"  ✓ {period_type.capitalize()} summary saved ({len(articles)} articles).")


def main():
    print("=== AI Processor run:", datetime.now(timezone.utc), "===")
    categorize_and_summarize_articles()
    build_rollup_summary("daily", 1)
    build_rollup_summary("weekly", 7)
    build_rollup_summary("monthly", 30)
    print("=== AI Processor complete ===")


if __name__ == "__main__":
    main()

"""
scraper.py
----------
Reads the list of websites to scrape from the Supabase "sources"
table (so new sites can be added later with NO code changes),
visits each listing page, pulls out article links + titles, opens
each article and grabs its text, and inserts new ones into the
"articles" table with status = 'Pending Verification'.

Run manually:   python scraper/scraper.py
Run daily:      handled by .github/workflows/daily_run.yml
"""

import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from datetime import datetime, timezone

# ---------------------------------------------------------------
# 1. Connect to Supabase using secrets (never hard-code real keys)
# ---------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_KEY environment variables are missing.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
REQUEST_TIMEOUT = 20


def fetch(url: str):
    """GET a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  ! Could not fetch {url}: {e}")
        return None


def extract_article_text(article_url: str) -> str:
    """Best-effort extraction of the main body text of an article page."""
    soup = fetch(article_url)
    if soup is None:
        return ""
    # Try common article containers first; fall back to all <p> tags.
    candidates = soup.select("article p, .article-content p, .post-content p, .entry-content p")
    if not candidates:
        candidates = soup.select("p")
    text = " ".join(p.get_text(" ", strip=True) for p in candidates)
    return text[:6000]  # keep it a reasonable size for the AI step


def already_scraped(url: str) -> bool:
    result = supabase.table("articles").select("id").eq("url", url).execute()
    return len(result.data) > 0


def scrape_source(source: dict):
    name = f'{source["site_name"]} / {source["section_name"]}'
    print(f"Scraping {name} -> {source['listing_url']}")
    soup = fetch(source["listing_url"])
    if soup is None:
        return

    links = soup.select(source["article_link_selector"])
    seen_urls = set()
    count = 0
    max_articles = source.get("max_articles_per_run", 15)

    for link in links:
        if count >= max_articles:
            break
        href = link.get("href")
        if not href:
            continue
        # normalise relative URLs
        if href.startswith("/"):
            href = source["base_url"].rstrip("/") + href
        if not href.startswith("http"):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)

        title = link.get_text(strip=True)
        if not title or len(title) < 8:
            # sometimes the link wraps an <img> only; try the parent block
            parent = link.find_parent()
            title_tag = parent.find(["h1", "h2", "h3", "h4", "h5"]) if parent else None
            title = title_tag.get_text(strip=True) if title_tag else title

        if not title:
            continue

        if already_scraped(href):
            continue

        print(f"  + New article: {title[:80]}")
        body_text = extract_article_text(href)

        record = {
            "source_id": source["id"],
            "title": title,
            "url": href,
            "raw_text": body_text,
            "category": source.get("default_category", "Economics"),
            "region": source.get("default_region", "Local"),
            "published_at": datetime.now(timezone.utc).isoformat(),
            "status": "Pending Verification",
        }
        try:
            supabase.table("articles").insert(record).execute()
            count += 1
        except Exception as e:
            print(f"  ! Insert failed for {href}: {e}")

        time.sleep(1)  # be polite to the target site

    print(f"  -> {count} new article(s) added from {name}")


def main():
    print("=== CBM News Digest — Scraper run:", datetime.now(timezone.utc), "===")
    sources_result = supabase.table("sources").select("*").eq("is_active", True).execute()
    sources = sources_result.data
    print(f"Loaded {len(sources)} active source(s) from the database.")

    for source in sources:
        try:
            scrape_source(source)
        except Exception as e:
            print(f"Source {source.get('site_name')} failed entirely: {e}")

    print("=== Scrape run complete ===")


if __name__ == "__main__":
    main()

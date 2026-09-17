"""
admin.py — Admin Verification Dashboard (Streamlit)
----------------------------------------------------
Deploy this on Streamlit Community Cloud (free) as its own app,
separate from the public site. Protected by a simple password
stored in Streamlit secrets (st.secrets["ADMIN_PASSWORD"]).

Lets you:
  - See newly scraped articles ("Pending Verification")
  - Edit the AI summary / category / region
  - Approve or reject each one
  - Add / edit / delete the sites the scraper watches (the
    "sources" table) — no code or redeploy needed.
"""

import streamlit as st
from supabase import create_client
from datetime import datetime, timezone

st.set_page_config(page_title="CBM News Digest — Admin", layout="wide")

# ---------------------------------------------------------------
# Connection + very simple password gate
# ---------------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 CBM News Digest — Admin Login")
    pwd = st.text_input("Enter admin password", type="password")
    if st.button("Log in"):
        if ADMIN_PASSWORD and pwd == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

st.title("🛠️ CBM News Digest — Admin Dashboard")

CATEGORIES = [
    "Economics", "Construction", "Tourism", "Regulation",
    "Political", "Oil Price (Local)", "Oil Price (World)",
]

tab_review, tab_sources, tab_summaries = st.tabs(
    ["📋 Review Articles", "🌐 Manage Sources", "🧾 Roll-up Summaries"]
)

# ---------------------------------------------------------------
# TAB 1 — Review / edit / approve / reject / delete articles
# ---------------------------------------------------------------
with tab_review:
    status_filter = st.selectbox(
        "Show articles with status:",
        ["Pending Verification", "Approved", "Rejected", "All"],
        index=0,
    )
    query = supabase.table("articles").select("*").order("scraped_at", desc=True)
    if status_filter != "All":
        query = query.eq("status", status_filter)
    articles = query.limit(200).execute().data

    st.caption(f"{len(articles)} article(s) shown.")

    for art in articles:
        with st.expander(f"[{art.get('category','—')}] {art['title']}", expanded=False):
            st.write(f"**Source URL:** {art['url']}")
            st.write(f"**Region:** {art.get('region','—')}  |  **Status:** {art['status']}")

            new_category = st.selectbox(
                "Category", CATEGORIES,
                index=CATEGORIES.index(art["category"]) if art.get("category") in CATEGORIES else 0,
                key=f"cat_{art['id']}",
            )
            new_region = st.selectbox(
                "Region", ["Local", "World"],
                index=0 if art.get("region", "Local") == "Local" else 1,
                key=f"region_{art['id']}",
            )
            current_summary = art.get("edited_summary") or art.get("ai_summary") or ""
            new_summary = st.text_area(
                "Summary (edit as needed)", value=current_summary, height=100,
                key=f"summary_{art['id']}",
            )

            col1, col2, col3, col4 = st.columns(4)
            if col1.button("💾 Save edits", key=f"save_{art['id']}"):
                supabase.table("articles").update({
                    "category": new_category,
                    "region": new_region,
                    "edited_summary": new_summary,
                }).eq("id", art["id"]).execute()
                st.success("Saved.")
                st.rerun()

            if col2.button("✅ Approve", key=f"approve_{art['id']}"):
                supabase.table("articles").update({
                    "status": "Approved",
                    "category": new_category,
                    "region": new_region,
                    "edited_summary": new_summary,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", art["id"]).execute()
                st.success("Approved — now visible on the public site.")
                st.rerun()

            if col3.button("🚫 Reject", key=f"reject_{art['id']}"):
                supabase.table("articles").update({
                    "status": "Rejected",
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", art["id"]).execute()
                st.rerun()

            if col4.button("🗑️ Delete permanently", key=f"delete_{art['id']}"):
                supabase.table("articles").delete().eq("id", art["id"]).execute()
                st.rerun()

# ---------------------------------------------------------------
# TAB 2 — Manage the list of scraped websites/sections
# ---------------------------------------------------------------
with tab_sources:
    st.subheader("Websites & sections the scraper watches")
    sources = supabase.table("sources").select("*").order("id").execute().data

    for src in sources:
        with st.expander(f"{src['site_name']} — {src['section_name']}"):
            listing_url = st.text_input("Listing page URL", src["listing_url"], key=f"url_{src['id']}")
            base_url = st.text_input("Base URL", src["base_url"], key=f"base_{src['id']}")
            selector = st.text_input(
                "Article link CSS selector", src["article_link_selector"], key=f"sel_{src['id']}"
            )
            default_category = st.selectbox(
                "Default category", CATEGORIES,
                index=CATEGORIES.index(src["default_category"]) if src["default_category"] in CATEGORIES else 0,
                key=f"defcat_{src['id']}",
            )
            is_active = st.checkbox("Active", value=src["is_active"], key=f"active_{src['id']}")
            max_articles = st.number_input(
                "Max articles per run", min_value=1, max_value=100,
                value=src.get("max_articles_per_run", 15), key=f"max_{src['id']}",
            )

            c1, c2 = st.columns(2)
            if c1.button("💾 Save", key=f"save_src_{src['id']}"):
                supabase.table("sources").update({
                    "listing_url": listing_url,
                    "base_url": base_url,
                    "article_link_selector": selector,
                    "default_category": default_category,
                    "is_active": is_active,
                    "max_articles_per_run": int(max_articles),
                }).eq("id", src["id"]).execute()
                st.success("Saved.")
                st.rerun()
            if c2.button("🗑️ Delete this source", key=f"del_src_{src['id']}"):
                supabase.table("sources").delete().eq("id", src["id"]).execute()
                st.rerun()

    st.divider()
    st.subheader("➕ Add a new website/section to scrape")
    with st.form("add_source"):
        f_site = st.text_input("Site name (e.g. Khmer Times)")
        f_section = st.text_input("Section name (e.g. Business)")
        f_listing = st.text_input("Listing/category page URL")
        f_base = st.text_input("Base URL (e.g. https://example.com)")
        f_selector = st.text_input("Article link CSS selector", value='a[href*="/article/"]')
        f_category = st.selectbox("Default category", CATEGORIES)
        f_region = st.selectbox("Default region", ["Local", "World"])
        submitted = st.form_submit_button("Add source")
        if submitted and f_site and f_listing and f_base:
            supabase.table("sources").insert({
                "site_name": f_site,
                "section_name": f_section or "General",
                "listing_url": f_listing,
                "base_url": f_base,
                "article_link_selector": f_selector,
                "default_category": f_category,
                "default_region": f_region,
                "is_active": True,
            }).execute()
            st.success("Source added — it will be scraped on the next run.")
            st.rerun()

# ---------------------------------------------------------------
# TAB 3 — Read-only view of the AI roll-up summaries
# ---------------------------------------------------------------
with tab_summaries:
    for period in ["daily", "weekly", "monthly"]:
        st.subheader(period.capitalize())
        rows = (
            supabase.table("summaries")
            .select("*")
            .eq("period_type", period)
            .order("period_start", desc=True)
            .limit(5)
            .execute()
            .data
        )
        for row in rows:
            st.markdown(f"**{row['period_start']} → {row['period_end']}** ({row['article_count']} articles)")
            st.write(row["summary_text"])
            st.divider()

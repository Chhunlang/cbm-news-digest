"""
public.py — Public Website (Streamlit)
----------------------------------------
Deploy separately from the admin app, on Streamlit Community Cloud
(free). Uses the SUPABASE ANON (public) key — NOT the service key —
so it can only ever read what Row Level Security allows, which is
Approved articles only (see database/schema.sql).
"""

import streamlit as st
from supabase import create_client
from datetime import date, timedelta

st.set_page_config(page_title="CBM News & Oil Price Digest", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]   # public/anon key, safe to expose
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

st.title("📰 CBM Cambodia — News & Oil Price Digest")
st.caption("Curated daily from Cambodian and global energy news sources. Verified content only.")

CATEGORIES = [
    "All", "Economics", "Construction", "Tourism", "Regulation",
    "Political", "Oil Price (Local)", "Oil Price (World)",
]

view = st.radio("View", ["Daily", "Weekly", "Monthly", "All time"], horizontal=True)
category = st.selectbox("Filter by category", CATEGORIES)

today = date.today()
if view == "Daily":
    start_date = today
elif view == "Weekly":
    start_date = today - timedelta(days=7)
elif view == "Monthly":
    start_date = today - timedelta(days=30)
else:
    start_date = None

query = supabase.table("public_articles").select("*").order("published_at", desc=True)
if category != "All":
    query = query.eq("category", category)
if start_date:
    query = query.gte("published_at", start_date.isoformat())

articles = query.limit(300).execute().data

st.divider()
st.caption(f"{len(articles)} approved article(s) match your filters.")

if not articles:
    st.info("No approved articles match this view yet. Check back after the next daily update.")

for art in articles:
    with st.container(border=True):
        st.markdown(f"#### [{art['title']}]({art['url']})")
        badge = f"`{art['category']}` · `{art['region']}`"
        st.caption(badge)
        st.write(art.get("summary") or "")
        if art.get("published_at"):
            st.caption(f"Published: {art['published_at'][:10]}")

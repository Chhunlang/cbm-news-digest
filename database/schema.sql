-- ============================================================
-- CBM News & Oil Price Digest — Database Schema
-- Target: Supabase (PostgreSQL)
-- How to use: Supabase Dashboard -> SQL Editor -> paste this
-- whole file -> Run.
-- ============================================================

-- 1. SOURCES: the list of websites/sections to scrape.
-- This is what makes the scraper "no-code extensible" — add a
-- row here (via the Admin Dashboard) and the scraper will pick
-- it up on the next run, no Python changes needed.
create table if not exists sources (
    id                bigint generated always as identity primary key,
    site_name         text not null,                 -- e.g. 'Cambodianess'
    section_name      text not null,                 -- e.g. 'Economics'
    listing_url       text not null,                 -- category/listing page to scrape
    base_url          text not null,                 -- e.g. 'https://cambodianess.com'
    -- CSS selectors used by the scraper (BeautifulSoup .select()).
    -- Kept as text so non-developers can tweak them from the Admin
    -- Dashboard if a site changes its layout, with no redeploy.
    article_link_selector   text not null default 'a[href*="/article/"]',
    title_selector          text,                     -- optional override; falls back to link text
    default_category        text not null default 'Economics',
    default_region           text not null default 'Local',  -- 'Local' or 'World'
    is_active                boolean not null default true,
    max_articles_per_run     int not null default 15,
    created_at               timestamptz not null default now(),
    updated_at               timestamptz not null default now()
);

-- 2. ARTICLES: every scraped item lives here.
create table if not exists articles (
    id                bigint generated always as identity primary key,
    source_id         bigint references sources(id) on delete set null,
    title             text not null,
    url               text not null unique,           -- prevents duplicate scraping
    raw_text          text,                           -- full scraped article body (for AI to read)
    ai_summary        text,                           -- 2-4 sentence AI summary
    edited_summary    text,                           -- admin's manually edited version (wins if set)
    category          text,                           -- Economics / Construction / Tourism / Regulation /
                                                       -- Political / Oil Price (Local) / Oil Price (World)
    region            text,                           -- 'Local' or 'World'
    published_at      timestamptz,                    -- best-guess publish date from the site
    scraped_at         timestamptz not null default now(),
    status             text not null default 'Pending Verification'
                        check (status in ('Pending Verification','Approved','Rejected')),
    reviewed_by         text,
    reviewed_at          timestamptz
);

create index if not exists idx_articles_status on articles(status);
create index if not exists idx_articles_category on articles(category);
create index if not exists idx_articles_published_at on articles(published_at desc);

-- 3. SUMMARIES: daily / weekly / monthly AI roll-ups.
create table if not exists summaries (
    id              bigint generated always as identity primary key,
    period_type     text not null check (period_type in ('daily','weekly','monthly')),
    period_start    date not null,
    period_end      date not null,
    summary_text    text not null,
    article_count   int not null default 0,
    generated_at    timestamptz not null default now(),
    unique (period_type, period_start)
);

-- 4. Helpful view: only what the PUBLIC website is allowed to show.
create or replace view public_articles as
select id, title, url, coalesce(edited_summary, ai_summary) as summary,
       category, region, published_at, scraped_at
from articles
where status = 'Approved'
order by published_at desc nulls last, scraped_at desc;

-- 5. Row Level Security (recommended). Supabase enables RLS by
-- default on new projects created via the dashboard UI; if you
-- created the table via SQL you must turn it on explicitly.
alter table articles enable row level security;
alter table sources enable row level security;
alter table summaries enable row level security;

-- Public (anon key) may only READ approved articles and summaries.
create policy "public can read approved articles"
  on articles for select
  using (status = 'Approved');

create policy "public can read summaries"
  on summaries for select
  using (true);

-- The scraper and admin dashboard connect with the SERVICE ROLE
-- key (kept secret in GitHub Actions / Streamlit secrets), which
-- bypasses RLS entirely — so no extra policies are needed for them.

-- 6. Seed the two sources requested (Cambodianess + OilPrice.com).
-- You can add more rows later from the Admin Dashboard.
insert into sources (site_name, section_name, listing_url, base_url, article_link_selector, default_category, default_region, max_articles_per_run)
values
  ('Cambodianess', 'Economics', 'https://cambodianess.com/economics', 'https://cambodianess.com', 'a[href*="/article/"]', 'Economics', 'Local', 15),
  ('Cambodianess', 'Politics',  'https://cambodianess.com/politics',  'https://cambodianess.com', 'a[href*="/article/"]', 'Political', 'Local', 15),
  ('Cambodianess', 'Society (Construction/Tourism/Regulation signals)', 'https://cambodianess.com/society', 'https://cambodianess.com', 'a[href*="/article/"]', 'Construction', 'Local', 15),
  ('OilPrice.com', 'World Oil Prices', 'https://oilprice.com/Energy/Oil-Prices/', 'https://oilprice.com', 'a[href*="/Energy/"]', 'Oil Price (World)', 'World', 15),
  ('OilPrice.com', 'World Energy News', 'https://oilprice.com/Latest-Energy-News/World-News/', 'https://oilprice.com', 'a[href*="/Latest-Energy-News/"]', 'Oil Price (World)', 'World', 15)
on conflict do nothing;

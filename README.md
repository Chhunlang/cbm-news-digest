# CBM News & Oil Price Digest — Full Setup Guide (Zero Coding Experience Needed)

This project automatically, every day:
1. Scrapes news from **cambodianess.com** and oil prices/news from **oilprice.com**
2. Uses free AI to sort each article into a category and write a short summary
3. Builds a Daily / Weekly (7-day) / Monthly (30-day) executive summary
4. Emails you that daily summary
5. Lets you (the admin) approve/edit/reject each article on a private dashboard
6. Publishes only the articles you approved to a public webpage

**Cost: $0/month**, using free tiers of GitHub, Supabase, Groq, Gmail, and Streamlit Community Cloud.

---

## 0. What you're setting up (in plain English)

| Piece | What it does | Where it lives | Tool used |
|---|---|---|---|
| Database | Stores every article, source website, and summary | Supabase | Supabase (free Postgres DB) |
| Scraper | Visits the news sites daily and saves new articles | Runs automatically | GitHub Actions (free cron job) |
| AI step | Reads each article, tags it, and summarizes it | Runs automatically | Groq (free AI API) |
| Email | Sends you the daily digest | Runs automatically | Your Gmail |
| Admin Dashboard | Private page where YOU approve/reject/edit articles | Your browser | Streamlit Community Cloud (free website) |
| Public Website | Public page showing only approved articles | Your browser / shared link | Streamlit Community Cloud (free website) |

You do **not** need to install Python or write any code. You'll copy files into a GitHub repository through the website, and click a few buttons.

---

## 1. Create your accounts (all free, ~15 minutes)

Do these in order:

### 1.1 GitHub (code + daily automation)
1. Go to https://github.com and click **Sign up**. Use your email, set a password and username.
2. Verify your email when GitHub sends you a confirmation.

### 1.2 Supabase (the database)
1. Go to https://supabase.com and click **Start your project** → sign in with your GitHub account (easiest).
2. Click **New project**.
   - Name: `cbm-news-digest`
   - Database password: click "Generate a password" and **save it somewhere safe** (a notes app), you likely won't need it directly but keep it.
   - Region: choose "Singapore" (closest to Cambodia).
3. Wait ~2 minutes while Supabase sets up your database.
4. Once it's ready, in the left sidebar click **SQL Editor** → **New query**.
5. Open the file `database/schema.sql` from this project (below), copy **all** of it, paste it into the SQL editor, and click **Run**.
   - This creates all the tables and adds Cambodianess + OilPrice.com as starting sources.
6. In the left sidebar, go to **Project Settings → API**. You'll need three values later — keep this tab open:
   - **Project URL** (looks like `https://xxxxx.supabase.co`)
   - **anon public key** (a long string)
   - **service_role key** (a long string — click "Reveal"). **Never share this one publicly** — it has full database access.

### 1.3 Groq (free AI for categorizing/summarizing)
1. Go to https://console.groq.com and sign up (free, no credit card).
2. Go to **API Keys** → **Create API Key**. Copy it and save it somewhere safe — Groq only shows it once.

### 1.4 Gmail App Password (for sending the daily email)
1. Use an existing Gmail account, or create a free one at https://accounts.google.com/signup.
2. Turn on 2-Step Verification: go to https://myaccount.google.com/security → **2-Step Verification** → follow the steps.
3. Then go to https://myaccount.google.com/apppasswords, sign in again if asked.
4. Under "App name" type `CBM News Digest` and click **Create**. Google shows you a 16-character password (like `abcd efgh ijkl mnop`). Copy it — this is your `GMAIL_APP_PASSWORD` (not your normal Gmail password).

### 1.5 Streamlit Community Cloud (free website hosting)
1. Go to https://streamlit.io/cloud and click **Sign up**, choose "Continue with GitHub."
2. Authorize Streamlit to access your GitHub account.

---

## 2. Put the project on GitHub

1. Go to https://github.com/new
   - Repository name: `cbm-news-digest`
   - Set it to **Private** (recommended, since it will reference your data — you can still deploy the Streamlit apps from a private repo for free).
   - Click **Create repository**.
2. On the new repo's page, click **uploading an existing file** (or **Add file → Upload files**).
3. Upload every file/folder from this project, keeping the same folder structure:
   ```
   cbm-news-digest/
   ├── .github/workflows/daily_run.yml
   ├── database/schema.sql
   ├── scraper/scraper.py
   ├── scraper/ai_processor.py
   ├── scraper/send_email.py
   ├── scraper/requirements.txt
   ├── admin_app/admin.py
   ├── public_app/public.py
   └── requirements.txt
   ```
   (GitHub's drag-and-drop uploader preserves folders if you drag the whole folder in, or you can create each folder by typing `foldername/filename` as you upload one file at a time.)
4. Click **Commit changes**.

---

## 3. Add your secret keys to GitHub Actions

These let the daily automated job connect to Supabase, Groq, and Gmail without ever putting your passwords in the code.

1. In your repo, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret** and add each of these one at a time (name exactly as shown, value from step 1):

   | Secret name | Value |
   |---|---|
   | `SUPABASE_URL` | your Supabase Project URL |
   | `SUPABASE_SERVICE_KEY` | your Supabase service_role key |
   | `GROQ_API_KEY` | your Groq API key |
   | `GMAIL_ADDRESS` | your Gmail address |
   | `GMAIL_APP_PASSWORD` | the 16-character app password |
   | `RECIPIENT_EMAIL` | the email address you want the digest sent to (can be the same Gmail address) |
   | `ADMIN_DASHBOARD_URL` | leave blank for now — you'll fill this in after step 5 |

3. To test it immediately instead of waiting for tomorrow: go to the **Actions** tab → click **Daily News & Oil Price Digest** → **Run workflow** → **Run workflow** (green button). Wait ~1-2 minutes, then click into the run to see it scrape, categorize, and email you.
   - The workflow already runs automatically every day at 07:30 Phnom Penh time — you don't need to do anything for that.

---

## 4. Deploy the Admin Dashboard (private, for you)

1. Go to https://share.streamlit.io (Streamlit Community Cloud) and click **Create app**.
2. Choose **"Deploy a public app from GitHub"** (it'll still be password-protected by the app itself, from step below).
3. Repository: `your-username/cbm-news-digest`. Branch: `main`. Main file path: `admin_app/admin.py`.
4. Before clicking Deploy, click **Advanced settings** → paste this into the **Secrets** box (replace with your real values):
   ```toml
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_SERVICE_KEY = "your-service-role-key"
   ADMIN_PASSWORD = "choose-any-password-you-will-remember"
   ```
5. Click **Deploy**. After ~1 minute you'll get a URL like `https://cbm-news-admin.streamlit.app`.
6. Go back to GitHub → **Settings → Secrets → Actions → `ADMIN_DASHBOARD_URL`** and paste this URL in (so your daily email includes a direct link).

Visit the URL, enter the `ADMIN_PASSWORD` you set, and you'll see every scraped article waiting for your review.

---

## 5. Deploy the Public Website

1. Back on https://share.streamlit.io, click **Create app** again.
2. Same repo, same branch, but Main file path: `public_app/public.py`.
3. In **Advanced settings → Secrets**, paste:
   ```toml
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_ANON_KEY = "your-anon-public-key"
   ```
   (Notice: this is the **anon** key, not the service key — the public site should never have full database access.)
4. Click **Deploy**. You'll get a second URL, e.g. `https://cbm-news-public.streamlit.app` — this is the link you can share with colleagues.

---

## 6. Your daily workflow going forward

Every morning around 07:30 (Phnom Penh time):
1. GitHub Actions scrapes both sites, runs the AI categorizer, builds the 3 summaries, and emails you.
2. You open the **Admin Dashboard** link, review the new "Pending Verification" articles, edit anything you want, and click **Approve** (or **Reject**/**Delete**).
3. Approved articles instantly appear on the **Public Website**, filterable by category and by Daily/Weekly/Monthly view.

To add a new website to scrape later (e.g. Khmer Times), go to the Admin Dashboard → **Manage Sources** tab → fill in the "Add a new website/section" form. No coding or redeploying needed.

---

## 7. How to adjust things later (no code required)

- **Change the daily run time:** edit `.github/workflows/daily_run.yml`, the line `- cron: "30 0 * * *"` (format is `minute hour * * *` in UTC time).
- **A site's layout changed and scraping stopped working:** go to Admin Dashboard → Manage Sources → update the "Article link CSS selector" field for that source. (If you're unsure what selector to use, ask a developer — or paste the site's page source into an AI chat and ask it for the right CSS selector.)
- **Add more categories:** edit the `CATEGORIES` list near the top of `scraper/ai_processor.py`, `admin_app/admin.py`, and `public_app/public.py` (keep all three in sync).
- **Switch the free AI provider:** the code uses Groq; to use Google Gemini's free tier instead, only `scraper/ai_processor.py`'s `call_llm()` function needs to change its URL/request format.

---

## 8. Troubleshooting

- **No email arrived:** check the GitHub **Actions** tab → click the latest run → look for red ❌ steps and read the error text. Most common cause: a secret name typo (they're case-sensitive).
- **Admin/Public site shows "KeyError" or blank:** double-check the **Secrets** box on Streamlit Cloud (Settings → gear icon → Secrets) matches the names used in the code exactly (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` / `SUPABASE_ANON_KEY`).
- **Scraper finds 0 articles:** the target site likely changed its HTML. Update the selector in Admin Dashboard → Manage Sources (see section 7).
- **Free tier limits:** Supabase free tier pauses a project after 7 days of total inactivity — the daily GitHub Action running queries against it every day prevents that automatically. Groq's free tier has a generous daily request limit that a two-site daily digest will not come close to hitting.

---

## Files in this project

```
cbm-news-digest/
├── README.md                        <- this guide
├── requirements.txt                  <- Python packages for the two Streamlit apps
├── database/
│   └── schema.sql                    <- run once in Supabase's SQL Editor
├── scraper/
│   ├── scraper.py                    <- visits sites, saves new articles
│   ├── ai_processor.py               <- categorizes, summarizes, builds roll-ups
│   ├── send_email.py                 <- emails you the daily digest
│   └── requirements.txt              <- Python packages for the scraper steps
├── admin_app/
│   └── admin.py                      <- private review/approve dashboard (Streamlit)
├── public_app/
│   └── public.py                     <- public website (Streamlit)
└── .github/workflows/
    └── daily_run.yml                 <- the daily automation schedule
```

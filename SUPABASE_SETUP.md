# Supabase Setup Guide

## 1. Create a Supabase project

1. Go to https://supabase.com → **New project** (free tier is fine)
2. Choose a name, password, and region (closest to Israel → eu-central-1)
3. Wait ~2 min for provisioning

## 2. Create the database table

1. In your project, open **SQL Editor**
2. Paste the contents of [`supabase/schema.sql`](supabase/schema.sql) and click **Run**

## 3. Get your API keys

In **Settings → API**:
- **Project URL** — looks like `https://abcxyzabc.supabase.co`
- **anon / public key** — safe to commit, read-only
- **service_role key** — secret, never commit

## 4. Update the frontend config

Edit [`docs/config.js`](docs/config.js) and fill in your values:

```js
const SUPABASE_URL = "https://abcxyzabc.supabase.co";
const SUPABASE_ANON_KEY = "eyJ...your anon key...";
```

Commit and push — the site will now read from Supabase.

## 5. Migrate existing data (one time)

```bash
pip install httpx

SUPABASE_URL=https://abcxyzabc.supabase.co \
SUPABASE_SERVICE_KEY=your_service_role_key \
python3 scripts/migrate_to_supabase.py
```

This uploads the existing `docs/data/alerts_history.json` (~442K records).
It takes about 3–5 minutes on the free tier.

## 6. Set up GitHub Actions secrets

In your GitHub repo → **Settings → Secrets and variables → Actions**,
add two secrets:

| Name | Value |
|------|-------|
| `SUPABASE_URL` | Your project URL |
| `SUPABASE_SERVICE_KEY` | Your service_role key |

The workflow in `.github/workflows/update_alerts.yml` will then run every 2 hours,
fetching new alerts from oref.org.il and upserting them into Supabase.

## 7. (Optional) Remove the old JSON file from git

Once migration is confirmed working, the large JSON file is no longer needed:

```bash
git rm docs/data/alerts_history.json docs/data/metadata.json
git commit -m "Remove static JSON data — now served from Supabase"
```

## 8. (Optional) Increase Supabase row limit

The default Supabase API returns max 1000 rows per request. The frontend handles
this with concurrent pagination, but you can raise it for faster loads:

**Settings → API → Max Rows** → set to `10000` (free tier supports this)

Then in `docs/config.js` (and `docs/comparison.js`) change `PAGE_SIZE` to `10000`.

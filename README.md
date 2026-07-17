# Author Tech Terms

Public data pipeline for the Tech Savvy Writers glossary of author-focused tech terms.

Pulls terms from a ClickUp list, transforms them into a clean JSON file, and serves that file from GitHub so it can be fetched by:

- The TSW website (`techsavvywriters.com/tech-terms`)
- DottHQ (the Base44 app)
- Anywhere else that wants author-friendly definitions

## The public data URL

Once this repo is on GitHub, the JSON is available at:

```
https://raw.githubusercontent.com/<your-github-username>/author-tech-terms/main/data/terms.json
```

Replace `<your-github-username>` with your actual GitHub username. This URL is what the TSW website and DottHQ will fetch.

## How it works

```
You update a term in ClickUp
        ↓
ClickUp webhook fires
        ↓
GitHub Action runs sync_terms.py
        ↓
Script pulls all Published tasks, transforms to JSON
        ↓
Commits data/terms.json (if it changed)
        ↓
TSW & DottHQ fetch the updated file
```

## Data structure

The generated `data/terms.json` looks like:

```json
{
  "generated_at": "2026-07-17T04:12:33.000000+00:00",
  "count": 70,
  "terms": [
    {
      "term": "API (Application Programming Interface)",
      "slug": "api",
      "letter": "A",
      "plain_english": "...",
      "tech_speak": "...",
      "example": "...",
      "recommendation": "...",
      "long_definition": "...",
      "category": "General Tech",
      "related_terms": ["integration", "automation", "webhook"],
      "related_dotthq_tool": ""
    }
  ]
}
```

Note: `Member Notes` is deliberately excluded from the public JSON. Member-only content stays in ClickUp and can be fetched separately by DottHQ if/when needed.

## First-time setup

### 1. Push this repo to GitHub

- Create a new public repository on GitHub named `author-tech-terms`
- Push these files to the `main` branch

### 2. Add GitHub Secrets

In the repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name | Value |
|---|---|
| `CLICKUP_API_TOKEN` | Your ClickUp personal API token (starts with `pk_`) |
| `CLICKUP_LIST_ID` | `90165742913` |

### 3. Run it manually the first time

- Go to the Actions tab in the repo
- Select "Sync Tech Terms from ClickUp"
- Click "Run workflow" → "Run workflow"
- Wait ~30 seconds for it to complete
- Check that `data/terms.json` now exists and contains your terms

### 4. Set up the ClickUp webhook (for on-demand updates)

There are two ways to fire the webhook — pick one:

**Option A: ClickUp Automation (easiest)**

1. Open the "Tech Terms Explained" list in ClickUp
2. Click Automations → Create automation
3. Trigger: "Status changes to Published"
4. Action: "Call webhook"
5. URL:

    ```
    https://api.github.com/repos/<your-github-username>/author-tech-terms/dispatches
    ```

6. Method: POST
7. Headers:

    ```
    Accept: application/vnd.github.v3+json
    Authorization: Bearer <github-personal-access-token>
    Content-Type: application/json
    ```

8. Body:

    ```json
    { "event_type": "clickup-term-update" }
    ```

You'll need a GitHub personal access token with `repo` scope. Create one at github.com → Settings → Developer settings → Personal access tokens.

**Option B: Skip the webhook, rely on daily schedule + manual trigger**

If setting up the webhook feels fiddly, the workflow also runs once a day automatically, and you can trigger it manually any time. Perfectly workable for a glossary that doesn't need instant updates.

## Local testing

To run the sync script on your own machine before pushing changes:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# Edit .env, add your real CLICKUP_API_TOKEN

export $(cat .env | xargs)  # loads .env into your shell
python scripts/sync_terms.py

cat data/terms.json | head -50
```

## Field name matching

The script auto-discovers ClickUp custom field IDs by matching against these exact field names. If you rename a field in ClickUp, update the `FIELD_NAMES` dict in `scripts/sync_terms.py`:

- `Slug`
- `Letter`
- `Plain English`
- `Tech Speak`
- `Example`
- `Recommendation`
- `Long Definition`
- `Category`
- `Related Terms`
- `Related DottHQ Tool`

`Member Notes` is intentionally not read.

## Task statuses

Only tasks with status `Published` are included in the JSON. Tasks in `Draft`, `Review`, or `Archived` are ignored.

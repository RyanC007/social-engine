# Setup Guide

**Social Engine** — designed and architected by Ryan Cunningham | [readyplangrow.com](https://readyplangrow.com)

---

## Prerequisites

Before you start, you need:

1. A [Blotato](https://blotato.com) account with your social media accounts connected
2. A Google account with Google Drive
3. A [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier works)
4. Python 3.11+ installed

---

## Step 1: Clone and Install

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/social-engine.git
cd social-engine
pip install -r requirements.txt
```

---

## Step 2: Create Your .env File

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Blotato API key (from your Blotato account settings)
BLOTATO_API_KEY=your_blotato_api_key_here

# Gemini API key (for AI content generation)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: second client API key
# SECOND_CLIENT_BLOTATO_API_KEY=their_blotato_api_key_here
```

---

## Step 3: Get Your Blotato Account and Template IDs

You need the account IDs for each connected social platform and the template IDs for visual generation.

**Get account IDs:**
1. Log into [Blotato](https://blotato.com)
2. Go to Settings > Connected Accounts
3. Note the account ID for each platform (LinkedIn, X, Instagram, Facebook, TikTok, YouTube)

**Get template IDs:**
1. Go to Templates in your Blotato dashboard
2. Note the template IDs you want to use for LinkedIn and Facebook infographics
3. Note the template path for Instagram quote cards and YouTube Shorts videos

---

## Step 4: Create Your Client Config

Copy the example client config:

```bash
cp clients/example_client.json clients/your_name.json
```

Edit `clients/your_name.json` and fill in:
- Your name and brand details
- Content pillars (your 5-7 topic areas)
- Blotato account IDs for each platform
- Blotato template IDs for visuals
- Google Drive folder IDs (see Step 5)
- Your email address for approval notifications

---

## Step 5: Set Up Google Drive

Create two folders in your Google Drive:
1. **Content Pipeline** — where your weekly post files will live
2. **Knowledge Base** — where your Voice DNA file lives

Note the folder IDs from the URL (the long string after `/folders/` in the Drive URL) and add them to your client config.

**One-time OAuth authorization:**

```bash
python setup_oauth.py --client your_name
```

This opens a browser window. Log in with your Google account and authorize the app. A `tokens/your_name_token.json` file is created and used for all future Drive operations.

---

## Step 6: Create Your Voice DNA File

Your Voice DNA is a plain text or Markdown file that describes your writing style, tone, and personality. The engine uses it when generating content.

Save it to your Knowledge Base Drive folder as `voice_dna.md`.

Include:
- How you write (tone, humor, directness)
- Words and phrases you use
- Words and phrases you never use
- Your content philosophy
- Examples of your best posts

---

## Step 7: Test the Pipeline

Run a dry-run to verify everything is connected:

```bash
python content_pipeline/pipeline_runner.py --client your_name --dry-run
```

This will:
- Connect to Google Drive
- Generate 7 days of content previews (nothing is saved or sent)
- Show you what the weekly email would look like

If everything looks right, run it for real:

```bash
python content_pipeline/pipeline_runner.py --client your_name
```

---

## Step 8: Set Up the Automated Schedule

The engine is designed to run from a cloud environment (like Manus) that stays on 24/7. The scheduled task runs every hour and handles:
- Sunday 6 PM: generate 7 days of content and send the approval email
- All other times: poll Gmail for your APPROVE ALL reply

If you are running this locally on a Mac, use the provided launchd plist:

```bash
bash launchd/install.sh your_name
```

If you are running this on a Linux server, add to crontab:

```bash
# Run every hour
0 * * * * cd /path/to/social-engine && python cloud_daily_run.py --client your_name --run
```

---

## Step 9: Your First Weekly Approval

Every Sunday at 6 PM (your configured timezone), you will receive an email with the full 7-day content preview.

Reply with one of:

| Reply | What happens |
|---|---|
| `APPROVE ALL` | All 7 days scheduled into Blotato at 9 AM each day |
| `APPROVE ALL SKIP 3` | All days except Day 3 scheduled |
| `APPROVE ALL SKIP 3 5 7` | All days except Days 3, 5, and 7 scheduled |
| `SKIP ALL` | Week discarded, nothing scheduled |

To edit or delete a scheduled post after approval, log into your Blotato dashboard.

---

## Adding a Second Client

To run the engine for a second person (e.g., a client or team member):

1. Create `clients/their_name.json` with their config
2. Add their email to `CLIENT_EMAIL_CONFIG` in `cloud_daily_run.py` and `weekly_approval.py`
3. Set their Blotato API key as `THEIR_NAME_BLOTATO_API_KEY` in `.env`
4. Run `python setup_oauth.py --client their_name` for their Google auth
5. Run `python cloud_daily_run.py --client their_name --run` in the scheduled task

---

## Troubleshooting

**"No content files found"**
The engine looks for `.md` files in your Content Pipeline Drive folder. Make sure files exist there with the correct frontmatter format (see `docs/CONTENT_TEMPLATE.md`).

**"Day X not found"**
The `current_day` in your state file is higher than the number of files in the folder. Reset it by editing `.state/your_name_cloud_state.json` and setting `current_day` to 1.

**"Gmail poll found no reply"**
Check your spam folder. The engine searches for emails from your own address with "Weekly Preview" in the subject. Make sure your reply goes to the same thread.

**Blotato API errors**
Double-check your account IDs and template IDs in your client config. Account IDs are numeric. Template IDs are either bare UUIDs (for infographic templates) or path-format strings (for video and quote card templates).

---

## Credits

Designed and architected by **Ryan Cunningham**
Founder, [Ready, Plan, Grow!](https://readyplangrow.com)

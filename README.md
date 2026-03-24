# Social Engine

**A personal brand content pipeline that generates, repurposes, and publishes across LinkedIn, X, Instagram, Facebook, TikTok, and YouTube Shorts — fully automated with a single weekly approval.**

Designed and architected by **Ryan Cunningham** | [readyplangrow.com](https://readyplangrow.com)

---

## What This Does

The Social Engine takes a single piece of long-form content (your LinkedIn post) and turns it into a full week of multi-platform content — automatically. You review everything in one Sunday email, reply `APPROVE ALL`, and the engine schedules all posts into [Blotato](https://blotato.com) at the right times.

**One approval. Seven days of content. Zero daily management.**

---

## How It Works

```
Sunday 6 PM
  Weekly pipeline generates 7 LinkedIn master posts
  (using your Voice DNA + content pillars + Golden Moments data)
        |
        v
  Each LinkedIn post is repurposed to:
  X  |  Instagram  |  Facebook  |  TikTok  |  YouTube Shorts
        |
        v
  You receive one email with the full 7-day preview
        |
        v
  Reply: APPROVE ALL
  (or:   APPROVE ALL SKIP 3 5  to skip specific days)
        |
        v
  All approved posts scheduled into Blotato at 9 AM your timezone
  Mon through Sun
        |
        v
  Edit or delete any post directly in the Blotato dashboard
```

---

## Architecture

| Layer | What it does |
|---|---|
| **Content Pipeline** | Generates 7 LinkedIn master posts from your Voice DNA and content pillars using Gemini AI |
| **Post Builder** | Derives all platform posts from the LinkedIn master — every platform stays on-topic |
| **Guardrails** | Strips em dashes, removes section labels, enforces engagement questions, blocks generic CTAs |
| **Blotato Publisher** | Submits each post with the correct template, account ID, and schedule time |
| **Weekly Approval** | Sends a 7-day preview email, parses your APPROVE ALL reply, bulk-schedules everything |

---

## Multi-Client Support

The engine supports multiple clients from a single codebase. Each client has their own:
- `clients/{slug}.json` config file (Blotato API key, account IDs, template rotation, content pillars)
- Voice DNA file on Google Drive
- Content pipeline folder on Google Drive
- Separate approval email flow

```bash
python cloud_daily_run.py --client your_client_slug --run
python cloud_daily_run.py --client your_second_client_slug --run
```

---

## Platforms Supported

| Platform | Content Type | Visual |
|---|---|---|
| LinkedIn | Long-form post | Auto-generated infographic (hook text as headline) |
| X (Twitter) | Short punchy post | None |
| Instagram | Caption + hashtags | Quote card template |
| Facebook | Conversational post | Auto-generated infographic |
| TikTok | Short-form script | None |
| YouTube Shorts | Video script | Auto-generated video via Blotato |

---

## Requirements

- Python 3.11+
- A [Blotato](https://blotato.com) account with connected social media accounts
- A Google Drive folder for your content pipeline
- A Google OAuth token (one-time browser auth, see setup guide)
- A Gemini API key (for AI content generation)

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_GITHUB_USERNAME/social-engine.git
cd social-engine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the example config and fill in your details
cp clients/example_client.json clients/your_client_slug.json
# Edit clients/your_client_slug.json with your Blotato IDs and Drive folder IDs

# 4. Set up your .env file
cp .env.example .env
# Edit .env with your API keys

# 5. One-time Google Drive auth (opens browser)
python setup_oauth.py --client your_client_slug

# 6. Run the weekly pipeline manually to test
python content_pipeline/pipeline_runner.py --client your_client_slug --dry-run

# 7. Deploy the hourly scheduled task (see docs/SETUP_GUIDE.md)
```

---

## Directory Structure

```
social-engine/
  clients/                  # Per-client config files (one JSON per client)
    example_client.json     # Template to copy and fill in
  content/                  # Content formatting modules
    hook_selector.py        # Viral hook library (client-aware)
    linkedin_builder.py     # LinkedIn post assembler
    repurposer.py           # Platform post derivation engine
  content_pipeline/         # Weekly content generation
    weekly_pipeline.py      # Generates 7 LinkedIn master posts
    post_builder.py         # Derives all platform posts from LinkedIn master
    pipeline_runner.py      # Full orchestrator with Drive upload and email
  engine/                   # Core engine modules
    client_config.py        # Client config loader
    drive.py                # Google Drive integration
    publisher.py            # Blotato visual generation
    workflow.py             # End-to-end publish workflow
  knowledge_base/           # Content parsing and Drive access
    content_parser.py       # Markdown frontmatter parser
    google_drive.py         # Drive file operations
  publisher/                # Blotato API client
    blotato.py              # All Blotato API calls
  docs/                     # Setup guides and content templates
  cloud_daily_run.py        # Main scheduled task runner
  weekly_approval.py        # Weekly email approval system
  auto_publish.py           # Direct publish without approval
  main.py                   # Interactive CLI for manual use
```

---

## Content Format

All content files use a simple Markdown format with YAML frontmatter. See `docs/CONTENT_TEMPLATE.md` for the full spec.

```markdown
---
title: Your Post Title
topic: your-topic-slug
day: 1
type: post
platforms: linkedin, x, instagram, facebook, tiktok, youtube_shorts
hashtags: #YourHashtag #AnotherHashtag
---

## Hook
Your opening line that stops the scroll.

## Body
Your main content. 3-5 paragraphs or bullet points.

## Engagement
What question do you want your audience to answer?
```

---

## Guardrails

The engine enforces these rules on every post before it publishes:

- No em dashes
- No section labels in published output (`## Hook`, `## Body` etc. are stripped)
- Every post must end with an engagement question
- No generic CTAs ("follow for more", "click the link", "link in bio")
- No unprovable claims ("game-changing", "unprecedented")

---

## Credits

Designed and architected by **Ryan Cunningham**
Founder, [Ready, Plan, Grow!](https://readyplangrow.com)

Built for founders and operators who want a personal brand pipeline that runs itself.

---

## License

MIT License. Use it, fork it, build on it.

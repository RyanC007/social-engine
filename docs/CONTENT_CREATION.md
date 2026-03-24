# Content Creation Guide

> Part of the **Social Engine** - designed and built by [Ryan Cunningham](https://www.readyplangrow.com) at [Ready, Plan, Grow!](https://www.readyplangrow.com)

The Social Engine does not generate your content. It takes content you have already written and automates everything after that - approval, image generation, scheduling, and publishing across all platforms.

This guide explains what you need to produce each week, what format it must be in, and how to get it into the engine using any AI content creation tool.

---

## The weekly content requirement

Before Sunday 6 PM UTC each week, your Google Drive content folder must contain up to 7 Markdown post files - one per day. The engine reads these files on Sunday evening, builds a preview email, and waits for your approval.

If the folder is empty on Sunday, the engine has nothing to work with and will skip that week.

---

## File format

Each post is a Markdown file with YAML frontmatter followed by three sections.

```markdown
---
type: linkedin
day: 1
topic: why-founders-struggle-with-delegation
client: your_client
platforms: linkedin, x, instagram, youtube_shorts, tiktok, facebook
hashtags: Leadership, Founders, Delegation, BusinessGrowth
---

## Hook

Most founders are not bad at delegating. They are bad at documenting.

## Body

The real problem is not trust. It is that the knowledge lives in your head.

When you delegate without documentation, you are not handing off a task.
You are handing off a puzzle with missing pieces.

The fix is not a better hire. It is a better handoff.

Three things every delegation needs:
- What done looks like (the output, not the process)
- Where to find the context (a doc, a Loom, a Slack thread)
- Who to ask if something breaks

That is it. No 10-page SOP. No management training. Just those three things.

## Engagement

What is the one thing you wish you had documented before you delegated it?
```

### Frontmatter fields

| Field | Required | Description |
|---|---|---|
| `type` | Yes | Always `linkedin` for the master post |
| `day` | Yes | Day number 1 - 7 (1 = Monday) |
| `topic` | Yes | Slug describing the post topic |
| `client` | Yes | Your client slug (matches your `clients/` config file) |
| `platforms` | Yes | Comma-separated list of platforms to publish to |
| `hashtags` | Yes | Comma-separated hashtags (no `#` prefix) |

### Section rules

- **Hook** - One or two lines. This is the scroll-stopper. It must stand alone.
- **Body** - Your main content. 150 - 400 words. Short paragraphs or bullets.
- **Engagement** - A single question to your audience. Must end with `?`.

---

## How to generate content with an AI tool

You can use any AI tool - ChatGPT, Claude, a custom agent, or your own workflow. Below is a practical example using a simple prompt approach.

### Example prompt (ChatGPT / Claude)

```
You are a content writer for [YOUR NAME], a [YOUR NICHE] expert.

Write 5 LinkedIn posts for this week. Each post should:
- Be written in [YOUR VOICE: e.g. direct, no-fluff, practical]
- Cover one of these topics: [LIST YOUR TOPICS]
- Follow this exact format:

---
type: linkedin
day: [DAY NUMBER]
topic: [topic-slug-here]
client: your_client
platforms: linkedin, x, instagram, youtube_shorts, tiktok, facebook
hashtags: [3-5 relevant hashtags, no # prefix]
---

## Hook
[One scroll-stopping opening line]

## Body
[150-300 words of practical content]

## Engagement
[One question for the audience ending with ?]

---

Generate all 5 posts now, one after the other.
```

### What to do with the output

1. Copy each post into a separate `.md` file
2. Name the files clearly: `post_day1_topic-slug.md`, `post_day2_topic-slug.md`, etc.
3. Upload them to your Google Drive content folder before Sunday 6 PM UTC

The engine will pick them up automatically on Sunday evening.

---

## Using the handoff script (for local content tools)

If your AI content tool saves files to a local directory rather than directly to Drive, use `golden_moments_handoff.py` to convert and upload them automatically.

### Setup

Open `golden_moments_handoff.py` and update the configuration section at the top:

```python
# Your Google Drive content folder ID (from the Drive URL)
DRIVE_CONTENT_FOLDERS = {
 "your_client": "YOUR_DRIVE_FOLDER_ID_HERE",
}

# Platforms to publish to
DEFAULT_PLATFORMS = {
 "your_client": "linkedin, x, instagram, youtube_shorts, tiktok, facebook",
}

# Default hashtags (used as fallback if not in the post file)
DEFAULT_HASHTAGS = {
 "your_client": "AI, Automation, Business",
}
```

Your content tool must save posts to this local directory structure:

```
content/
 your_client-personal/
 linkedin/
 2026-w13/
 post_day1_topic-slug.md
 post_day2_topic-slug.md
...
```

### Run the handoff

```bash
# Preview what will be converted (no files written)
python golden_moments_handoff.py --client your_client --dry-run

# Run the full handoff for the current week
python golden_moments_handoff.py --client your_client

# Run for a specific week
python golden_moments_handoff.py --client your_client --week 2026-W14
```

The script will:
1. Read your local post files
2. Convert them to the Social Engine format (adds frontmatter if missing)
3. Upload them to a new `Week-N` subfolder in your Drive content folder
4. Update the engine state so the Sunday pipeline picks them up

---

## Drive folder structure

The engine expects your content folder in Drive to contain `Week-N` subfolders:

```
Your Drive Content Folder/
 Week-1/
 post_day1_topic-slug.md
 post_day2_topic-slug.md
...
 Week-2/
 post_day1_topic-slug.md
...
```

The engine always reads from the highest-numbered `Week-N` folder. Create a new subfolder each week and upload your files there.

---

## Checklist: before Sunday 6 PM UTC

- [ ] 5 - 7 post files created (one per day)
- [ ] Each file has correct frontmatter (`type`, `day`, `topic`, `client`, `platforms`, `hashtags`)
- [ ] Each file has `## Hook`, `## Body`, and `## Engagement` sections
- [ ] `## Engagement` ends with a `?`
- [ ] Files uploaded to a new `Week-N` subfolder in your Drive content folder

Once this is done, the engine handles everything else.

---

## About

The Social Engine was designed and built by **Ryan Cunningham**, founder of [Ready, Plan, Grow!](https://www.readyplangrow.com) - an AI-powered business growth platform for founders and operators.

Learn more at [readyplangrow.com](https://www.readyplangrow.com)
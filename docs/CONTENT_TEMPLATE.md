# Social Engine Content File Template

> Part of the **Social Engine** - designed and built by [Ryan Cunningham](https://www.readyplangrow.com) at [Ready, Plan, Grow!](https://www.readyplangrow.com)

This is the **canonical format** for all content files dropped into Google Drive.
Your content creation tool MUST output files in this exact format.

---

## File Naming Convention

```
post_day{N}_{slug}.md # short-form social post (1-5 paragraphs)
article_day{N}_{slug}.md # long-form LinkedIn article with YouTube Short script
```

Examples:
- `post_day1_ai-knowledge-base.md`
- `article_day3_gtm-strategy-founders.md`

---

## Required Frontmatter

Every file MUST begin with a YAML frontmatter block:

```yaml
---
type: post
day: 1
topic: Why Your AI Knowledge Base Is the Most Valuable Asset You Will Build This Year
client: ryan
platforms: linkedin, x, instagram, youtube_shorts, tiktok, facebook
hashtags: AI, AIAgents, BusinessAutomation, AIForBusiness, Entrepreneur
---
```

| Field | Required | Values |
|---|---|---|
| `type` | Yes | `post` or `article` |
| `day` | Yes | Integer (1-7 per week) |
| `topic` | Yes | Full topic sentence |
| `client` | Recommended | `your_client_slug` |
| `platforms` | Yes | Comma-separated platform list |
| `hashtags` | Yes | Comma-separated, no # prefix |

---

## Post Format (type: post)

```markdown
---
type: post
day: 1
topic: Why Your AI Knowledge Base Is the Most Valuable Asset You Will Build This Year
client: ryan
platforms: linkedin, x, instagram, youtube_shorts, tiktok, facebook
hashtags: AI, AIAgents, BusinessAutomation, AIForBusiness, Entrepreneur
---

## Hook

Most business owners are using AI like a search engine.
That is the wrong move.

## Body

Your AI knowledge base is the difference between an AI that gives you generic answers
and one that knows your business, your clients, your voice, and your goals.

Here is what goes into a real knowledge base:

- Your brand voice and writing style
- Your ICP (who you serve and what keeps them up at night)
- Your service offerings and pricing logic
- Your past wins and case studies
- Your SOPs and internal processes

Once it is built, every AI tool you use gets dramatically better overnight.

## Engagement

Have you built a knowledge base for your business yet, and if not, what is stopping you?
```

**Rules:**
- No em dashes (use periods or commas instead)
- `## Engagement` section MUST end with a question mark
- No generic CTAs ("Follow for more", "Like and subscribe", etc.)
- Keep Hook under 3 lines
- Body: 150-300 words for posts

---

## Article Format (type: article)

```markdown
---
type: article
day: 3
topic: The GTM Strategy That Helped 3 Founders Hit Six Figures in 90 Days
client: client_b
platforms: linkedin, x, instagram, youtube_shorts, tiktok, facebook
hashtags: GTMStrategy, BusinessGrowth, MarketingStrategy, Founder, Leadership
---

## Title

The GTM Strategy That Helped 3 Founders Hit Six Figures in 90 Days

## Hook

Most founders build a product and then figure out how to sell it.
That is backwards, and it costs them months.

## Body

A go-to-market strategy is not a launch plan. It is a system.

[Full article body here -- 400-800 words]

## Key Takeaway

The founders who win in the first 90 days are not the ones with the best product.
They are the ones who knew exactly who they were selling to before they built anything.

## Engagement

What is the one thing you wish you had known before you launched your first product or service?

## YouTube Short Script

HOOK:
Most founders build first and sell second. That is the mistake.

INSIGHT:
A real GTM strategy starts with your customer, not your product.
You need to know who you are selling to, what they are afraid of, and where they spend their time.

ENGAGEMENT:
What would your launch have looked like if you had a clear GTM strategy from day one?
```

**Rules:**
- `## YouTube Short Script` is required for articles
- Script MUST have HOOK, INSIGHT, and ENGAGEMENT sections
- ENGAGEMENT in script MUST end with a question mark
- No em dashes anywhere in the file
- Key Takeaway: 1-2 sentences max

---

## Drive Folder Structure

```
RPG Shared Drive (0AK8dAs_XgfnNUk9PVA)
 └── Ryan Content Pipeline/
 ├── Week-1/
 │ ├── post_day1_ai-knowledge-base.md
 │ ├── post_day2_automation-systems.md
 │ ├── article_day3_founders-flywheel.md
 │ ├── post_day4_ai-agents.md
 │ └── post_day5_seo-ai.md
 └── Week-2/
 └──...

 └── Client B Content Pipeline/
 ├── Week-1/
 │ ├── post_day1_financial-projections.md
 │ └──...
 └── Week-2/
 └──...
```

The engine reads files from the folder configured in `clients/{slug}.json` under `drive.content_folder_id`.
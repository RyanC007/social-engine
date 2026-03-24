"""
Weekly Content Pipeline for Ryan's Personal Brand.

Runs every Sunday at 6:00 PM UTC.

WHAT IT DOES:
1. Pulls the latest Golden Moments synthesis from the Drive content folder
2. Reads the current week's synthesis (weekly_synthesis_YYYY-WNN.md) if available
3. Uses the Gemini API to generate 7 days of LinkedIn-first content
4. Enforces topic pillar rotation (AI Architecture, Getting Started with AI, Founders Flywheel, etc.)
5. Enforces all guardrails (no click links, no generic CTAs, no em dashes, engagement question mandatory)
6. Writes 7 post files to the Drive content pipeline folder in the correct frontmatter format
7. Sends Ryan an email summary of what was generated

TOPIC PILLARS (must rotate across 7 days, no same pillar on consecutive days):
  P1: AI Architecture       - How AI systems are built, agent design, infrastructure
  P2: Getting Started AI    - Practical first steps, demystifying AI for founders
  P3: Founders Flywheel     - Ryan's framework: build, measure, iterate, compound
  P4: Knowledge Building    - Knowledge bases, documentation, AI fuel
  P5: Brand Building        - Personal brand, authority, content systems
  P6: AI Automation         - Workflows, time savings, ROI of automation
  P7: Thought Leadership    - Hot takes, contrarian views, industry observations

CADENCE (7 days = 1 full week):
  Day 1 (Mon): P1 or P2 - Educational/Tactical (40% of mix)
  Day 2 (Tue): P3 or P6 - Story-Based or Tactical
  Day 3 (Wed): P4 or P7 - Thought Leadership (30% of mix)
  Day 4 (Thu): P2 or P5 - Educational/Tactical
  Day 5 (Fri): P1 or P3 - Tactical or Story-Based (20% story mix)
  Day 6 (Sat): P6 or P7 - Engagement/Question (10% engagement mix)
  Day 7 (Sun): P4 or P5 - Thought Leadership or Brand Building

GUARDRAILS (enforced by post_validator.py before writing to Drive):
  - No "click here", "link in bio", "check out my link", "visit my profile"
  - No "follow me", "follow for more", "like and share"
  - No em dashes (use periods or commas)
  - No unprovable claims ("the only", "unprecedented", "game-changing")
  - No client names (use "a client" or "a business we work with")
  - No internal repo URLs, file paths, or agent infrastructure details
  - Engagement section MUST end with a question mark
  - Body MUST be 150-300 words
  - Hook MUST be under 3 lines
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

# Add parent directory to path for engine imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from content.hook_selector import suggest_hooks, apply_hook
    HOOK_SELECTOR_AVAILABLE = True
except ImportError:
    HOOK_SELECTOR_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# Topic pillar definitions
PILLARS = {
    "P1": {
        "name": "AI Architecture",
        "description": "How AI systems are designed and built. Agent design, infrastructure, multi-agent orchestration, system architecture for founders.",
        "angles": [
            "Here's what most founders get wrong about AI architecture...",
            "The real difference between an AI tool and an AI system...",
            "What a production AI agent system actually looks like...",
            "Why your AI stack needs an architect, not just a builder...",
        ],
        "hashtags": ["#AIArchitecture", "#AIAgents", "#BuildInPublic", "#FoundersFlywheel", "#AI"],
    },
    "P2": {
        "name": "Getting Started with AI",
        "description": "Practical first steps for founders who want to use AI but don't know where to start. Demystifying AI, avoiding common mistakes, first wins.",
        "angles": [
            "If I were starting with AI today, here's where I'd begin...",
            "The first AI system every small business should build...",
            "Stop buying AI tools. Start building AI systems...",
            "3 questions to ask before you invest in any AI solution...",
        ],
        "hashtags": ["#AIForBusiness", "#SmallBusiness", "#AIStrategy", "#Automation", "#Founders"],
    },
    "P3": {
        "name": "Founders Flywheel",
        "description": "Ryan's proprietary framework. Build, measure, iterate, compound. Momentum in business growth. Systems that create self-reinforcing results.",
        "angles": [
            "The Founders Flywheel isn't a metaphor. It's a system...",
            "Compounding is not just for investors. Here's how it works for founders...",
            "Why most founders plateau and how to break through...",
            "The one habit that separates founders who scale from those who stall...",
        ],
        "hashtags": ["#FoundersFlywheel", "#Founders", "#BuildInPublic", "#SmallBusiness", "#Growth"],
    },
    "P4": {
        "name": "Knowledge Building",
        "description": "Knowledge bases, documentation as competitive advantage, AI fuel, institutional knowledge in small teams.",
        "angles": [
            "Your AI is only as good as the knowledge you feed it...",
            "The knowledge problem nobody talks about...",
            "Documentation is not busywork. It's your competitive moat...",
            "How to build a knowledge base that actually makes your AI smarter...",
        ],
        "hashtags": ["#KnowledgeManagement", "#AI", "#SmallBusiness", "#FoundersFlywheel", "#Automation"],
    },
    "P5": {
        "name": "Brand Building",
        "description": "Personal brand authority, content systems, building trust without corporate budgets, storytelling for founders.",
        "angles": [
            "Building brand authority without a marketing budget...",
            "The content system that runs while you sleep...",
            "Why your personal brand is your most valuable business asset...",
            "Storytelling is not a soft skill. It's a revenue driver...",
        ],
        "hashtags": ["#PersonalBrand", "#ContentMarketing", "#Founders", "#BuildInPublic", "#SmallBusiness"],
    },
    "P6": {
        "name": "AI Automation",
        "description": "Practical automation workflows, time savings, ROI of automation, what to automate first, automation mistakes.",
        "angles": [
            "The first thing every founder should automate...",
            "I automated this process and got back 10 hours a week...",
            "Why most automation projects fail before they start...",
            "The ROI of automation for small businesses is not what you think...",
        ],
        "hashtags": ["#Automation", "#AIAutomation", "#SmallBusiness", "#Productivity", "#AI"],
    },
    "P7": {
        "name": "Thought Leadership",
        "description": "Hot takes, contrarian views, industry observations, uncomfortable truths about AI and business.",
        "angles": [
            "Hot take: most AI advice for small businesses is wrong...",
            "Everyone talks about AI tools. Nobody talks about AI strategy...",
            "The uncomfortable truth about AI adoption for founders...",
            "Unpopular opinion: the best AI system is the one you built yourself...",
        ],
        "hashtags": ["#AI", "#ThoughtLeadership", "#Founders", "#BuildInPublic", "#SmallBusiness"],
    },
}

# 7-day rotation schedule
WEEKLY_ROTATION = [
    {"day": 1, "label": "Monday",    "pillar": "P1", "type": "Educational"},
    {"day": 2, "label": "Tuesday",   "pillar": "P3", "type": "Story-Based"},
    {"day": 3, "label": "Wednesday", "pillar": "P7", "type": "Thought Leadership"},
    {"day": 4, "label": "Thursday",  "pillar": "P2", "type": "Educational"},
    {"day": 5, "label": "Friday",    "pillar": "P6", "type": "Tactical"},
    {"day": 6, "label": "Saturday",  "pillar": "P4", "type": "Thought Leadership"},
    {"day": 7, "label": "Sunday",    "pillar": "P5", "type": "Engagement"},
]

# Guardrail patterns to block
BLOCKED_PATTERNS = [
    r"click here",
    r"link in bio",
    r"check out my link",
    r"visit my profile",
    r"follow me",
    r"follow for more",
    r"like and share",
    r"share this post",
    r"\u2014",           # em dash
    r"\u2013",           # en dash used as em dash
    r"game.changing",
    r"unprecedented",
    r"the only [a-z]+ that",
    r"DM me",
    r"send me a message",
]


# ---------------------------------------------------------------------------
# Guardrail validator
# ---------------------------------------------------------------------------

def validate_post(text: str) -> list:
    """Returns a list of violations found in the post text."""
    violations = []
    text_lower = text.lower()

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text_lower):
            violations.append(f"Blocked pattern found: '{pattern}'")

    # Check engagement section ends with question
    engagement_match = re.search(r"## Engagement\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if engagement_match:
        engagement_text = engagement_match.group(1).strip()
        if not engagement_text.endswith("?"):
            violations.append("Engagement section does not end with a question mark")
    else:
        violations.append("No ## Engagement section found")

    # Check body word count
    body_match = re.search(r"## Body\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if body_match:
        body_text = body_match.group(1).strip()
        word_count = len(body_text.split())
        if word_count < 100:
            violations.append(f"Body too short: {word_count} words (minimum 100)")
        if word_count > 350:
            violations.append(f"Body too long: {word_count} words (maximum 350)")

    return violations


# ---------------------------------------------------------------------------
# Content generation via Gemini
# ---------------------------------------------------------------------------

def _get_hook_directive(day_config: dict) -> str:
    """
    Pull a curated viral hook from the hook library and return it as a
    directive string for the Gemini prompt. Maps post type to hook intent.
    """
    if not HOOK_SELECTOR_AVAILABLE:
        return "Write a strong opening hook that stops the scroll. Bold statement or pattern interrupt. No em dashes. Under 3 lines."

    # Map post type to hook intent
    intent_map = {
        "Educational":        "authority",
        "Story-Based":        "revelation",
        "Thought Leadership": "contrarian",
        "Tactical":           "results",
        "Engagement":         "curiosity",
    }
    post_type = day_config.get("type", "Educational")
    intent = intent_map.get(post_type, "authority")
    client_slug = day_config.get("client", "your_client")

    try:
        hooks = suggest_hooks(
            content_type="post",
            intent=intent,
            platform="linkedin",
            client_slug=client_slug,
            limit=3,
        )
        if hooks:
            # Provide 3 options so Gemini can pick the best fit for the topic
            options = "\n".join(
                f"  Option {i+1}: {h.template}  (e.g. {h.example})"
                for i, h in enumerate(hooks[:3])
            )
            return (
                f"Use one of these proven viral hook frameworks as the structural basis for your ## Hook section.\n"
                f"Adapt it to fit the specific topic and golden moments context. Do NOT copy it verbatim.\n"
                f"{options}"
            )
    except Exception:
        pass

    return "Write a strong opening hook that stops the scroll. Bold statement or pattern interrupt. No em dashes. Under 3 lines."


def generate_post_with_gemini(
    day_config: dict,
    golden_moments_context: str,
    week_label: str,
    previous_topics: list,
) -> str:
    """Generate a single post using Gemini API."""
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return _generate_fallback_post(day_config, week_label)

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    pillar = PILLARS[day_config["pillar"]]
    angle_options = "\n".join(f"  - {a}" for a in pillar["angles"])
    hashtags = " ".join(pillar["hashtags"])
    previous = ", ".join(previous_topics) if previous_topics else "none yet"

    # Pull a curated viral hook from the hook library
    hook_directive = _get_hook_directive(day_config)

    prompt = f"""You are writing a LinkedIn post for YOUR_NAME, co-founder of Your Brand Name (RPG).

RYAN'S VOICE:
- Direct, strategic, authority-building
- Anti-BS. Calls out industry nonsense without being arrogant
- First person, personal and specific
- Generation X founder who left corporate in 2023/2024 and built something real
- Practical, not theoretical. The story is the work, not the tool
- Contrarian but grounded in real experience
- Never preachy, never corporate

THIS WEEK'S GOLDEN MOMENTS (use these as inspiration and raw material):
{golden_moments_context if golden_moments_context else "No golden moments available this week. Draw from general AI architecture and founder experience themes."}

POST SPECIFICATIONS:
- Week: {week_label}
- Day: {day_config['day']} ({day_config['label']})
- Topic Pillar: {pillar['name']} - {pillar['description']}
- Post Type: {day_config['type']}
- Topics already covered this week (DO NOT repeat): {previous}

ANGLE OPTIONS (choose the most relevant to the golden moments context, or create a better one in the same spirit):
{angle_options}

OPENING HOOK DIRECTIVE:
{hook_directive}

OUTPUT FORMAT (use exactly this structure):
---
type: post
day: {day_config['day']}
topic: [3-5 word topic slug, e.g., "ai-architecture-for-founders"]
client: ryan
pillar: {day_config['pillar']}
pillar_name: {pillar['name']}
platforms: linkedin, x, instagram, threads, facebook, tiktok, youtube_shorts
hashtags: {hashtags}
---

## Hook
[First 1-3 lines. Must stop the scroll. A bold statement, a specific result, or a pattern interrupt. No em dashes. No generic openers like "I want to share" or "Today I learned".]

## Body
[150-300 words. 3-5 short paragraphs. Specific, concrete, personal. Reference the golden moments context where relevant but anonymize any client details. No em dashes. No "click here" or "link in bio" or "follow me". Active voice. Second person where appropriate.]

## Engagement
[One single question that is specific to the post topic. Must end with a question mark. Not generic like "What do you think?" but specific like "What's the first protocol you'd automate in your business?" or "Where does your AI system break down when the data goes stale?"]

MANDATORY GUARDRAILS:
- No em dashes (use periods or commas instead)
- No "click here", "link in bio", "follow me", "follow for more", "like and share"
- No unprovable claims ("the only", "unprecedented", "game-changing")
- No client names (use "a client" or "a business we work with")
- No internal tool names, file paths, or repo references
- Engagement section MUST end with a question mark
- Body must be 150-300 words
- Hook must be under 3 lines

Write the post now:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"  Gemini error: {e}. Using fallback.")
        return _generate_fallback_post(day_config, week_label)


def _generate_fallback_post(day_config: dict, week_label: str) -> str:
    """Fallback post template when Gemini is unavailable."""
    pillar = PILLARS[day_config["pillar"]]
    hashtags = " ".join(pillar["hashtags"])
    angle = pillar["angles"][0]

    return f"""---
type: post
day: {day_config['day']}
topic: {pillar['name'].lower().replace(' ', '-')}-{week_label.lower().replace(' ', '-')}
client: ryan
pillar: {day_config['pillar']}
pillar_name: {pillar['name']}
platforms: linkedin, x, instagram, threads, facebook, tiktok, youtube_shorts
hashtags: {hashtags}
---

## Hook
{angle}

## Body
[DRAFT - Gemini unavailable. Replace this section with 150-300 words on the topic: {pillar['name']}. 

Context: {pillar['description']}

Use Ryan's voice: direct, specific, anti-BS, first person, practical over theoretical.]

## Engagement
What is the one thing about {pillar['name'].lower()} that you wish someone had told you before you started?"""


# ---------------------------------------------------------------------------
# Golden Moments loader
# ---------------------------------------------------------------------------

def load_golden_moments_context(client_slug: str = "your_client") -> str:
    """
    Load the most recent weekly synthesis from the local content directory.
    Falls back to checking the Drive folder path if local files are not found.
    """
    # Check local repo content directory first
    content_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "content", "ryan-personal", "synthesis"
    )

    if os.path.exists(content_dir):
        synthesis_files = sorted([
            f for f in os.listdir(content_dir)
            if f.startswith("weekly_synthesis") and f.endswith(".md")
        ], reverse=True)

        if synthesis_files:
            latest = os.path.join(content_dir, synthesis_files[0])
            print(f"  Loading golden moments from: {synthesis_files[0]}")
            with open(latest) as f:
                content = f.read()
            # Extract just the content opportunities and key themes sections
            # to keep the context focused and within token limits
            sections = []
            for section_title in ["Key Themes", "Content Opportunities", "Key Events"]:
                match = re.search(
                    rf"## {section_title}.*?\n(.*?)(?=\n## |\Z)",
                    content, re.DOTALL
                )
                if match:
                    sections.append(f"### {section_title}\n{match.group(1).strip()}")
            return "\n\n".join(sections) if sections else content[:3000]

    print("  No local synthesis found. Proceeding without golden moments context.")
    return ""


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def write_post_file(post_content: str, day: int, output_dir: str) -> str:
    """Write a post to the output directory in the correct filename format."""
    # Extract topic slug from frontmatter
    topic_match = re.search(r"^topic:\s*(.+)$", post_content, re.MULTILINE)
    topic_slug = topic_match.group(1).strip() if topic_match else f"day{day}-post"
    # Clean the slug
    topic_slug = re.sub(r"[^a-z0-9\-]", "", topic_slug.lower().replace(" ", "-"))

    filename = f"post_day{day}_{topic_slug}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        f.write(post_content)

    return filepath


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(client_slug: str = "your_client", output_dir: str = None, dry_run: bool = False):
    """Run the full weekly content pipeline."""
    now = datetime.now(timezone.utc)
    # ISO week label
    week_label = f"{now.year}-W{now.isocalendar()[1]:02d}"
    next_week = now + timedelta(days=7)
    next_week_label = f"{next_week.year}-W{next_week.isocalendar()[1]:02d}"

    print(f"\n[{client_slug}] Weekly Content Pipeline")
    print(f"  Generating content for: {next_week_label}")
    print(f"  Dry run: {dry_run}")
    print()

    # Set output directory
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(__file__), "..", ".state",
            f"{client_slug}_pipeline_{next_week_label}"
        )
    os.makedirs(output_dir, exist_ok=True)

    # Load golden moments context
    print("Step 1: Loading Golden Moments context...")
    golden_context = load_golden_moments_context(client_slug)
    print(f"  Context loaded: {len(golden_context)} chars")

    # Generate 7 posts
    print("\nStep 2: Generating 7 days of content...")
    generated_files = []
    previous_topics = []
    violations_summary = []

    for day_config in WEEKLY_ROTATION:
        day = day_config["day"]
        pillar = PILLARS[day_config["pillar"]]
        print(f"  Day {day} ({day_config['label']}) - {pillar['name']}...")

        post_content = generate_post_with_gemini(
            day_config=day_config,
            golden_moments_context=golden_context,
            week_label=next_week_label,
            previous_topics=previous_topics,
        )

        # Validate
        violations = validate_post(post_content)
        if violations:
            print(f"    Violations found: {violations}")
            violations_summary.append({
                "day": day,
                "pillar": pillar["name"],
                "violations": violations,
            })

        if not dry_run:
            filepath = write_post_file(post_content, day, output_dir)
            generated_files.append(filepath)
            print(f"    Written: {os.path.basename(filepath)}")
        else:
            print(f"    [DRY RUN] Would write: post_day{day}_{pillar['name'].lower().replace(' ', '-')}.md")

        previous_topics.append(pillar["name"])

    # Summary
    print(f"\nStep 3: Pipeline complete.")
    print(f"  Files generated: {len(generated_files)}")
    print(f"  Output directory: {output_dir}")
    if violations_summary:
        print(f"  Violations to review: {len(violations_summary)}")

    return {
        "week": next_week_label,
        "files": generated_files,
        "output_dir": output_dir,
        "violations": violations_summary,
        "dry_run": dry_run,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly content pipeline")
    parser.add_argument("--client", default="your_client", help="Client slug")
    parser.add_argument("--output-dir", help="Override output directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    result = run_pipeline(
        client_slug=args.client,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )

    if result["violations"]:
        print("\nViolations requiring review:")
        for v in result["violations"]:
            print(f"  Day {v['day']} ({v['pillar']}): {v['violations']}")

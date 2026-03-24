"""
Post Builder - derives all platform posts from the LinkedIn master post.

This is the single source of truth rule enforcer:
  LinkedIn post is ALWAYS the master.
  X, Instagram, Threads, Facebook, TikTok, YouTube Shorts are ALL derived from it.
  No platform post can introduce a topic, claim, or CTA not present in the LinkedIn post.

PLATFORM DERIVATION RULES:
  LinkedIn:   Full post (Hook + Body + Engagement). 150-300 words. 3-5 hashtags.
  X:          Hook only + engagement question. Max 280 chars. 1-2 hashtags.
  Instagram:  Hook + condensed body (3 key points) + engagement. 2200 char limit. 5-10 hashtags.
  Threads:    Hook + 1 key insight + engagement question. Max 500 chars.
  Facebook:   Full post (same as LinkedIn). Slightly warmer tone allowed.
  TikTok:     Script: Hook (3s) + 3 punchy points + engagement question. 150 words max.
  YouTube:    Script: Hook (5s) + expanded insight + engagement question. 200 words max.

GUARDRAILS (applied to ALL platforms):
  - No "click here", "link in bio", "check out my link", "visit my profile"
  - No "follow me", "follow for more", "like and share", "share this post"
  - No em dashes (use periods or commas)
  - No unprovable claims ("the only", "unprecedented", "game-changing")
  - No client names (use "a client" or "a business we work with")
  - No internal repo URLs, file paths, or agent infrastructure details
  - Engagement section MUST end with a question mark
  - All platform posts MUST be topically consistent with the LinkedIn master post
"""
import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

BLOCKED_PATTERNS = [
    (r"click here",         "click here"),
    (r"link in bio",        "link in bio"),
    (r"check out my link",  "check out my link"),
    (r"visit my profile",   "visit my profile"),
    (r"follow me\b",        "follow me"),
    (r"follow for more",    "follow for more"),
    (r"like and share",     "like and share"),
    (r"share this post",    "share this post"),
    (r"\u2014",             "em dash"),
    (r"\u2013",             "en dash"),
    (r"game.changing",      "game-changing"),
    (r"unprecedented",      "unprecedented"),
    (r"the only [a-z]+ that", "the only X that"),
    (r"dm me\b",            "DM me"),
    (r"send me a message",  "send me a message"),
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MasterPost:
    """Parsed LinkedIn master post."""
    raw: str
    hook: str = ""
    body: str = ""
    engagement: str = ""
    hashtags: list = field(default_factory=list)
    topic: str = ""
    pillar: str = ""
    day: int = 1
    client: str = "your_client_slug"


@dataclass
class PlatformPost:
    """A derived post for a specific platform."""
    platform: str
    text: str
    hashtags: list = field(default_factory=list)
    violations: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_master_post(filepath: str) -> MasterPost:
    """Parse a post markdown file into a MasterPost object."""
    with open(filepath) as f:
        content = f.read()

    post = MasterPost(raw=content)

    # Parse frontmatter
    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        topic_m = re.search(r"^topic:\s*(.+)$", fm, re.MULTILINE)
        pillar_m = re.search(r"^pillar:\s*(.+)$", fm, re.MULTILINE)
        day_m = re.search(r"^day:\s*(\d+)$", fm, re.MULTILINE)
        client_m = re.search(r"^client:\s*(.+)$", fm, re.MULTILINE)
        hashtags_m = re.search(r"^hashtags:\s*(.+)$", fm, re.MULTILINE)

        if topic_m:
            post.topic = topic_m.group(1).strip()
        if pillar_m:
            post.pillar = pillar_m.group(1).strip()
        if day_m:
            post.day = int(day_m.group(1).strip())
        if client_m:
            post.client = client_m.group(1).strip()
        if hashtags_m:
            raw_tags = hashtags_m.group(1).strip()
            post.hashtags = [t.strip() for t in raw_tags.split() if t.startswith("#")]

    # Parse sections
    hook_m = re.search(r"## Hook\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    body_m = re.search(r"## Body\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    eng_m = re.search(r"## Engagement\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)

    if hook_m:
        post.hook = hook_m.group(1).strip()
    if body_m:
        post.body = body_m.group(1).strip()
    if eng_m:
        post.engagement = eng_m.group(1).strip()

    return post


# ---------------------------------------------------------------------------
# Guardrail validator
# ---------------------------------------------------------------------------

def validate_text(text: str) -> list:
    """Returns list of violations in the text."""
    violations = []
    text_lower = text.lower()
    for pattern, label in BLOCKED_PATTERNS:
        if re.search(pattern, text_lower):
            violations.append(f"Blocked: '{label}'")
    return violations


def clean_text(text: str) -> str:
    """Auto-fix common guardrail violations."""
    # Remove em dashes
    text = text.replace("\u2014", ",")
    text = text.replace("\u2013", ",")
    # Remove follow CTAs
    text = re.sub(r"follow me for more.*?\.", "", text, flags=re.IGNORECASE)
    text = re.sub(r"follow for more.*?\.", "", text, flags=re.IGNORECASE)
    text = re.sub(r"like and share.*?\.", "", text, flags=re.IGNORECASE)
    # Remove link CTAs
    text = re.sub(r"link in bio.*?\.", "", text, flags=re.IGNORECASE)
    text = re.sub(r"click here.*?\.", "", text, flags=re.IGNORECASE)
    return text.strip()


# ---------------------------------------------------------------------------
# Platform derivers
# ---------------------------------------------------------------------------

def derive_linkedin(post: MasterPost) -> PlatformPost:
    """LinkedIn: full post, clean, no labels."""
    text = f"{post.hook}\n\n{post.body}\n\n{post.engagement}"
    if post.hashtags:
        text += "\n\n" + " ".join(post.hashtags[:5])
    text = clean_text(text)
    return PlatformPost(
        platform="linkedin",
        text=text,
        hashtags=post.hashtags[:5],
        violations=validate_text(text),
    )


def derive_x(post: MasterPost) -> PlatformPost:
    """X (Twitter): hook + engagement question. Max 280 chars."""
    # Take first line of hook
    hook_first_line = post.hook.split("\n")[0].strip()
    # Take engagement question
    engagement = post.engagement.strip()

    # Build tweet
    candidate = f"{hook_first_line}\n\n{engagement}"
    if len(candidate) > 280:
        # Truncate hook to fit
        max_hook = 280 - len(engagement) - 4
        hook_first_line = hook_first_line[:max_hook].rsplit(" ", 1)[0] + "..."
        candidate = f"{hook_first_line}\n\n{engagement}"

    # Add 1-2 hashtags if space allows
    if post.hashtags and len(candidate) + len(post.hashtags[0]) + 2 <= 280:
        candidate += f"\n\n{post.hashtags[0]}"

    candidate = clean_text(candidate)
    return PlatformPost(
        platform="x",
        text=candidate,
        hashtags=post.hashtags[:2],
        violations=validate_text(candidate),
    )


def derive_instagram(post: MasterPost) -> PlatformPost:
    """Instagram: hook + 3 key points from body + engagement. Up to 2200 chars."""
    # Extract up to 3 key sentences from body
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", post.body) if len(s.strip()) > 20]
    key_points = sentences[:3]
    body_condensed = "\n\n".join(key_points)

    text = f"{post.hook}\n\n{body_condensed}\n\n{post.engagement}"
    # Instagram allows more hashtags
    if post.hashtags:
        text += "\n\n" + " ".join(post.hashtags[:10])

    text = clean_text(text)
    if len(text) > 2200:
        text = text[:2197] + "..."

    return PlatformPost(
        platform="instagram",
        text=text,
        hashtags=post.hashtags[:10],
        violations=validate_text(text),
    )


def derive_threads(post: MasterPost) -> PlatformPost:
    """Threads: hook + 1 key insight + engagement. Max 500 chars."""
    # Take first sentence of body as the key insight
    first_sentence = re.split(r"(?<=[.!?])\s+", post.body.strip())[0]
    candidate = f"{post.hook.split(chr(10))[0]}\n\n{first_sentence}\n\n{post.engagement}"

    if len(candidate) > 500:
        max_insight = 500 - len(post.hook.split("\n")[0]) - len(post.engagement) - 8
        first_sentence = first_sentence[:max_insight].rsplit(" ", 1)[0] + "..."
        candidate = f"{post.hook.split(chr(10))[0]}\n\n{first_sentence}\n\n{post.engagement}"

    candidate = clean_text(candidate)
    return PlatformPost(
        platform="threads",
        text=candidate,
        hashtags=[],
        violations=validate_text(candidate),
    )


def derive_facebook(post: MasterPost) -> PlatformPost:
    """Facebook: same as LinkedIn. Slightly warmer tone is acceptable."""
    text = f"{post.hook}\n\n{post.body}\n\n{post.engagement}"
    if post.hashtags:
        text += "\n\n" + " ".join(post.hashtags[:5])
    text = clean_text(text)
    return PlatformPost(
        platform="facebook",
        text=text,
        hashtags=post.hashtags[:5],
        violations=validate_text(text),
    )


def derive_tiktok(post: MasterPost) -> PlatformPost:
    """TikTok: spoken script. Hook (3s) + 3 punchy points + engagement. Max 150 words."""
    # Extract 3 punchy points from body
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", post.body) if len(s.strip()) > 15]
    points = sentences[:3]

    hook_line = post.hook.split("\n")[0].strip()
    script_parts = [hook_line, ""]
    for i, point in enumerate(points, 1):
        script_parts.append(f"{i}. {point}")
    script_parts.append("")
    script_parts.append(post.engagement)

    text = "\n".join(script_parts)
    text = clean_text(text)

    # Enforce word count
    words = text.split()
    if len(words) > 150:
        text = " ".join(words[:150]) + "..."

    return PlatformPost(
        platform="tiktok",
        text=text,
        hashtags=post.hashtags[:5],
        violations=validate_text(text),
    )


def derive_youtube_short(post: MasterPost) -> PlatformPost:
    """YouTube Short: spoken script. Hook (5s) + expanded insight + engagement. Max 200 words."""
    hook_line = post.hook.split("\n")[0].strip()

    # Take first 2-3 sentences of body for the insight
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", post.body) if len(s.strip()) > 15]
    insight = " ".join(sentences[:3])

    script = f"{hook_line}\n\n{insight}\n\n{post.engagement}"
    script = clean_text(script)

    words = script.split()
    if len(words) > 200:
        script = " ".join(words[:200]) + "..."

    return PlatformPost(
        platform="youtube",
        text=script,
        hashtags=post.hashtags[:3],
        violations=validate_text(script),
    )


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

DERIVERS = {
    "linkedin": derive_linkedin,
    "x": derive_x,
    "instagram": derive_instagram,
    "threads": derive_threads,
    "facebook": derive_facebook,
    "tiktok": derive_tiktok,
    "youtube": derive_youtube_short,
}


def build_all_platforms(filepath: str, output_dir: Optional[str] = None) -> dict:
    """
    Parse a master post file and derive all platform posts from it.
    Returns a dict of {platform: PlatformPost}.
    """
    print(f"\nBuilding platform posts from: {os.path.basename(filepath)}")

    post = parse_master_post(filepath)
    print(f"  Topic: {post.topic} | Pillar: {post.pillar} | Day: {post.day}")

    results = {}
    all_violations = []

    for platform, deriver in DERIVERS.items():
        platform_post = deriver(post)
        results[platform] = platform_post

        if platform_post.violations:
            all_violations.append((platform, platform_post.violations))
            print(f"  {platform:12s}: {len(platform_post.text):4d} chars | VIOLATIONS: {platform_post.violations}")
        else:
            print(f"  {platform:12s}: {len(platform_post.text):4d} chars | OK")

    # Write output files if output_dir provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(filepath))[0]

        for platform, platform_post in results.items():
            out_path = os.path.join(output_dir, f"{base}_{platform}.md")
            with open(out_path, "w") as f:
                f.write(f"# {platform.upper()} - Day {post.day}: {post.topic}\n\n")
                f.write(platform_post.text)
                if platform_post.violations:
                    f.write(f"\n\n<!-- VIOLATIONS: {platform_post.violations} -->")
            print(f"  Written: {os.path.basename(out_path)}")

    if all_violations:
        print(f"\n  Total violations: {sum(len(v) for _, v in all_violations)}")

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build all platform posts from a LinkedIn master post")
    parser.add_argument("input", help="Path to the master post markdown file")
    parser.add_argument("--output-dir", help="Directory to write platform-specific post files")
    parser.add_argument("--platform", help="Build only a specific platform (linkedin|x|instagram|threads|facebook|tiktok|youtube)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    results = build_all_platforms(args.input, output_dir=args.output_dir)

    if args.platform:
        if args.platform in results:
            print(f"\n--- {args.platform.upper()} POST ---")
            print(results[args.platform].text)
        else:
            print(f"Unknown platform: {args.platform}")
            print(f"Available: {list(results.keys())}")

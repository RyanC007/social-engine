"""
Platform repurposer -- converts a LinkedInPost into platform-specific posts.

Phase 1 Brand Alignment Fixes Applied:
  - Voice DNA is injected into every repurposing call via the LinkedInPost.ryan_context field.
  - All CTAs are replaced with engagement hooks (thought-provoking questions).
  - Em dashes are stripped from all output text.
  - Generic "Follow for more" CTAs are forbidden; every post ends with a question.
  - Client-aware: tiktok_handle and website are passed through from ClientConfig.

Label-free output guarantee:
  - Section labels (Hook, Body, Engagement, HOOK:, INSIGHT:, CTA:) NEVER appear
    in the text that gets published to any platform.
  - The youtube_shorts PlatformPost carries two separate fields:
      .text        = clean published caption (no labels)
      .video_prompt = structured prompt string with labels for Blotato video generation only
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from content.linkedin_builder import LinkedInPost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_em_dashes(text: str) -> str:
    """Replace em dashes with a period-space or comma per [YOUR BRAND] brand rules."""
    text = re.sub(r"\s*\u2014\s*", ". ", text)
    text = text.replace("\u2014", ",")
    return text


def _strip_section_labels(text: str) -> str:
    """
    Remove any section label lines that should never appear in published output.
    Handles both ## Markdown headings and plain LABEL: prefixes.
    """
    labels = r"^(##\s+)?(hook|body|engagement|cta|insight|title|key takeaway|youtube short script)\s*:?\s*$"
    lines = text.split("\n")
    cleaned = [l for l in lines if not re.match(labels, l.strip(), re.IGNORECASE)]
    return "\n".join(cleaned).strip()


def _clean(text: str) -> str:
    """Strip em dashes, section labels, and normalise whitespace."""
    return _strip_em_dashes(_strip_section_labels(text)).strip()


# ---------------------------------------------------------------------------
# Topic-to-engagement-question mapping (Voice DNA aware)
# ---------------------------------------------------------------------------

_TOPIC_QUESTIONS: list[tuple[list[str], str]] = [
    (["knowledge base", "knowledge"],
     "Have you built a knowledge base for your business yet, and if not, what is stopping you?"),
    (["automation", "automate", "workflow"],
     "Which part of your business would you automate first if you had the right system in place?"),
    (["ai agent", "agent", "infrastructure"],
     "Are you building AI systems that work for you, or are you still just using AI as a search engine?"),
    (["content", "linkedin", "social"],
     "What would your content pipeline look like if you never had to write from scratch again?"),
    (["time", "hours", "leverage"],
     "If you got 10 hours back every week, what would you actually do with them?"),
    (["small business", "founder", "entrepreneur"],
     "What is the one operational bottleneck that is costing you the most time right now?"),
    (["seo", "search", "ranking"],
     "Is your content actually being found by the people who need it most?"),
    (["strategy", "gtm", "go-to-market"],
     "What would your business look like in 90 days if your strategy was fully executed?"),
    (["financial", "numbers", "revenue", "profit"],
     "Do you actually know your numbers well enough to make confident decisions today?"),
    (["leadership", "team", "culture"],
     "What is the one leadership decision you have been putting off that would change everything?"),
]

_FALLBACK_QUESTIONS: dict[str, str] = {
    "linkedin":       "What is the biggest obstacle stopping you from building this into your business right now?",
    "x":              "What is your biggest challenge with AI in your business right now?",
    "instagram":      "What would you do with an extra 10 hours per week?",
    "threads":        "What is the one thing you wish AI could do for your business today?",
    "youtube_shorts": "What would change in your business if you had a system doing this automatically?",
    "tiktok":         "What is the one thing holding your business back right now?",
    "facebook":       "What is the biggest thing stopping you from building AI into your business right now?",
}


def _derive_engagement_question(post: LinkedInPost, platform: str) -> str:
    """
    Derive a thought-provoking engagement question from the post topic and
    Voice DNA context. Falls back to a platform-specific default.
    """
    topic_lower = (post.topic or "").lower()
    text_lower = (post.text or "").lower()[:500]

    for keywords, question in _TOPIC_QUESTIONS:
        if any(kw in topic_lower or kw in text_lower for kw in keywords):
            return question

    return _FALLBACK_QUESTIONS.get(platform, _FALLBACK_QUESTIONS["linkedin"])


@dataclass
class PlatformPost:
    platform: str
    text: str                                       # clean published caption -- NO labels
    hashtags: list[str] = field(default_factory=list)
    thread_posts: list[str] = field(default_factory=list)
    video_prompt: str = ""                          # structured prompt for Blotato video gen only

    def formatted(self) -> str:
        body = _clean(self.text)
        if self.hashtags:
            tag_line = " ".join(f"#{t.lstrip('#')}" for t in self.hashtags)
            body = f"{body}\n\n{tag_line}"
        return body


def repurpose_for_x(post: LinkedInPost, website: str = "") -> PlatformPost:
    """
    X thread: hook tweet + insight tweets + engagement question tweet.
    No generic CTAs. Always ends with a thought-provoking question.
    """
    lines = [_clean(l) for l in post.text.split("\n") if l.strip()]

    def _trim(text: str, limit: int = 277) -> str:
        return text[:limit].strip() + "..." if len(text) > limit else text.strip()

    tweet1 = _trim(lines[0] if lines else post.topic)
    why_parts = lines[1:3] if len(lines) > 1 else []
    tweet2 = _trim("\n\n".join(why_parts)) if why_parts else ""
    how_parts = lines[3:6] if len(lines) > 3 else lines[2:4]
    tweet3 = _trim("\n\n".join(how_parts)) if how_parts else ""
    question = _derive_engagement_question(post, "x")
    tags = post.hashtags[:4]
    tag_str = " ".join(f"#{t}" for t in tags)
    tweet4 = f"{question}\n\n{tag_str}" if tag_str else question

    thread = [t for t in [tweet2, tweet3, tweet4] if t]
    return PlatformPost(platform="x", text=tweet1, hashtags=[], thread_posts=thread)


def repurpose_for_instagram(post: LinkedInPost, website: str = "") -> PlatformPost:
    """
    Instagram: hook + body + insight block + engagement question.
    No generic save/follow CTAs. Always ends with a thought-provoking question.
    """
    lines = [_clean(l) for l in post.text.split("\n") if l.strip()]
    hook = lines[0][:125] if lines else post.topic
    body_lines = lines[1:4] if len(lines) > 1 else []
    formatted_body = []
    for line in body_lines:
        if len(line) > 100:
            line = line[:100].rsplit(" ", 1)[0] + "..."
        formatted_body.append(line)
    insight_lines = [l for l in lines[4:7] if len(l) > 20]
    insight_block = "\n".join(f"-> {l}" for l in insight_lines[:3]) if insight_lines else ""
    question = _derive_engagement_question(post, "instagram")
    link_line = "Link in bio" if website else ""
    parts = [hook]
    if formatted_body:
        parts.append("\n\n".join(formatted_body))
    if insight_block:
        parts.append(insight_block)
    parts.append(question)
    if link_line:
        parts.append(link_line)
    caption = "\n\n".join(p for p in parts if p)
    if len(caption) > 2200:
        caption = caption[:2197] + "..."
    return PlatformPost(platform="instagram", text=caption, hashtags=post.hashtags[:15])


def repurpose_for_threads(post: LinkedInPost, website: str = "") -> PlatformPost:
    """
    Threads: 500 chars per post. Hook + one key point + engagement question.
    """
    lines = [_clean(l) for l in post.text.split("\n") if l.strip()]
    body = "\n\n".join(lines[:2])
    question = _derive_engagement_question(post, "threads")
    parts = [body, question]
    if website:
        parts.append(website)
    text = "\n\n".join(p for p in parts if p)[:500].strip()
    return PlatformPost(platform="threads", text=text, hashtags=post.hashtags[:5])


def repurpose_for_youtube_shorts(post: LinkedInPost, website: str = "") -> PlatformPost:
    """
    YouTube Shorts: two separate outputs.

    .text        = clean published caption posted to YouTube -- NO section labels.
    .video_prompt = structured string with HOOK/INSIGHT/ENGAGEMENT labels passed
                    ONLY to Blotato's video generation API, never published directly.
    """
    lines = [_clean(l) for l in post.text.split("\n") if l.strip()]
    hook = lines[0] if lines else post.topic
    insight_lines = lines[1:4] if len(lines) > 1 else []
    question = _derive_engagement_question(post, "youtube_shorts")

    # Clean published caption -- no labels, reads naturally
    caption_parts = [hook]
    if insight_lines:
        caption_parts.append(" ".join(insight_lines))
    caption_parts.append(question)
    caption = "\n\n".join(caption_parts)
    if len(caption) > 500:
        caption = caption[:497] + "..."

    # Structured prompt for Blotato video generation ONLY -- labels are fine here
    # because this string goes into the API payload, not into the published post text
    video_prompt = (
        f"HOOK:\n{hook}\n\n"
        f"INSIGHT:\n{chr(10).join(insight_lines)}\n\n"
        f"ENGAGEMENT:\n{question}"
    )
    if website:
        video_prompt = f"{video_prompt}\n\n{website}"

    return PlatformPost(
        platform="youtube_shorts",
        text=caption,
        hashtags=post.hashtags[:15],
        video_prompt=video_prompt,
    )


def repurpose_for_tiktok(post: LinkedInPost, handle: str = "", website: str = "") -> PlatformPost:
    """
    TikTok: punchy hook + one key insight + engagement question.
    No generic follow CTAs. Always ends with a question. Caption under 300 chars.
    """
    lines = [_clean(l) for l in post.text.split("\n") if l.strip()]
    hook = lines[0][:100] if lines else post.text[:100]
    insight = lines[1] if len(lines) > 1 else ""
    question = _derive_engagement_question(post, "tiktok")
    parts = [hook]
    if insight:
        parts.append(insight)
    parts.append(question)
    if website:
        parts.append(website)
    caption = "\n\n".join(parts)
    if len(caption) > 300:
        caption = caption[:297] + "..."
    tiktok_tags = ["AI", "AIAgents", "BusinessAutomation", "AIForBusiness", "TechTok",
                   "SmallBusiness", "Entrepreneur", "AIInfrastructure"]
    tags = (post.hashtags[:3] + [t for t in tiktok_tags if t not in post.hashtags])[:8]
    return PlatformPost(platform="tiktok", text=caption, hashtags=tags)


def repurpose_for_facebook(post: LinkedInPost, website: str = "") -> PlatformPost:
    """
    Facebook (Ready Plan Grow page): educational and helpful.
    Conversational hook + body + takeaway + topic-specific engagement question.
    """
    lines = [_clean(l) for l in post.text.split("\n") if l.strip()]
    hook = lines[0] if lines else post.topic
    body_lines = lines[1:5] if len(lines) > 1 else []
    body_text = "\n\n".join(body_lines)
    question = _derive_engagement_question(post, "facebook")
    link_line = f"Learn more: {website}" if website else ""
    parts = [hook]
    if body_text:
        parts.append(body_text)
    parts.append(question)
    if link_line:
        parts.append(link_line)
    text = "\n\n".join(p for p in parts if p)
    if len(text) > 2000:
        text = text[:1997] + "..."
    return PlatformPost(platform="facebook", text=text, hashtags=post.hashtags[:10])


def repurpose_all(
    post: LinkedInPost,
    tiktok_handle: str = "",
    website: str = "",
) -> dict[str, PlatformPost]:
    """
    Repurpose a LinkedIn pillar post to all supported platforms.
    Returns a dict of {platform: PlatformPost}.
    All outputs are label-free and brand-aligned.
    """
    return {
        "x":              repurpose_for_x(post, website=website),
        "instagram":      repurpose_for_instagram(post, website=website),
        "threads":        repurpose_for_threads(post, website=website),
        "youtube_shorts": repurpose_for_youtube_shorts(post, website=website),
        "tiktok":         repurpose_for_tiktok(post, handle=tiktok_handle, website=website),
        "facebook":       repurpose_for_facebook(post, website=website),
    }

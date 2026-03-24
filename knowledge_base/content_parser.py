"""
Parses Manus-generated content files from Google Drive.

File naming convention:
  post_day{N}_{slug}.md      -- short-form social post
  article_day{N}_{slug}.md   -- long-form LinkedIn article

Frontmatter fields (REQUIRED for Drive sync):
  type:       post | article
  day:        integer
  topic:      string
  client:     ryan | marcela  (optional, used for multi-client routing)
  platforms:  comma-separated list (e.g. linkedin, x, instagram, youtube_shorts, tiktok, facebook)
  hashtags:   comma-separated list (e.g. AI, AIAgents, BusinessAutomation)

Body sections (use ## Heading format):
  ## Hook
  ## Body
  ## Engagement      <-- replaces ## CTA; must end with a question mark
  ## Title           (articles only)
  ## Key Takeaway    (articles only)
  ## YouTube Short Script  (articles only)

Note: ## CTA is still supported for backwards compatibility but is deprecated.
      The engine will enforce that the engagement section ends with a question.
"""
import re
from dataclasses import dataclass, field


@dataclass
class ContentFile:
    filename: str
    content_type: str          # "post" or "article"
    day: int
    topic: str
    platforms: list[str]
    hashtags: list[str]
    raw_body: str              # full markdown body after frontmatter

    # Parsed sections
    hook: str = ""
    body: str = ""
    cta: str = ""
    title: str = ""            # articles only
    key_takeaway: str = ""     # articles only
    youtube_script: str = ""   # articles only

    def is_post(self) -> bool:
        return self.content_type == "post"

    def is_article(self) -> bool:
        return self.content_type == "article"

    def display_label(self) -> str:
        icon = "📝" if self.is_post() else "📄"
        return f"{icon} Day {self.day}  - {self.topic} [{self.content_type.upper()}]"

    def linkedin_text(self) -> str:
        """Assemble the LinkedIn-ready text from parsed sections."""
        if self.is_post():
            parts = [self.hook, self.body, self.cta]
        else:
            parts = [
                f"**{self.title}**" if self.title else "",
                self.hook,
                self.body,
                self.key_takeaway,
                self.cta,
            ]
        return "\n\n".join(p.strip() for p in parts if p.strip())


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML-ish frontmatter and return (meta dict, remaining body)."""
    meta = {}
    body = text
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = text[fm_match.end():]
        for line in fm_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip().lower()] = val.strip()
    return meta, body


def _extract_section(body: str, heading: str) -> str:
    """Pull the content under a ## Heading from the markdown body."""
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _type_from_filename(filename: str) -> str:
    name = filename.lower()
    if name.startswith("article"):
        return "article"
    if name.startswith("post"):
        return "post"
    # Fall back to frontmatter  - caller handles this
    return ""


def _day_from_filename(filename: str) -> int:
    match = re.search(r"day(\d+)", filename.lower())
    return int(match.group(1)) if match else 0


def parse_content_file(filename: str, raw_text: str) -> ContentFile:
    """Parse a single Manus content file into a ContentFile object."""
    meta, body = _parse_frontmatter(raw_text)

    content_type = meta.get("type") or _type_from_filename(filename) or "post"
    day = int(meta.get("day", 0)) or _day_from_filename(filename)
    topic = meta.get("topic", filename.replace(".md", "").replace("-", " ").replace("_", " "))
    platforms_raw = meta.get("platforms", "linkedin, x, instagram")
    hashtags_raw = meta.get("hashtags", "")

    platforms = [p.strip() for p in platforms_raw.split(",") if p.strip()]

    # These platforms are always in rotation regardless of what Manus specifies
    for always_on in ("youtube_shorts", "tiktok", "facebook"):
        if always_on not in platforms:
            platforms.append(always_on)
    hashtags = [h.strip().lstrip("#") for h in hashtags_raw.split(",") if h.strip()]

    cf = ContentFile(
        filename=filename,
        content_type=content_type,
        day=day,
        topic=topic,
        platforms=platforms,
        hashtags=hashtags,
        raw_body=body,
    )

    cf.hook = _extract_section(body, "Hook")
    cf.body = _extract_section(body, "Body")
    # Support both ## Engagement (preferred) and ## CTA (deprecated)
    engagement = _extract_section(body, "Engagement")
    cta_fallback = _extract_section(body, "CTA")
    raw_cta = engagement or cta_fallback
    # Enforce: engagement section must end with a question
    if raw_cta and not raw_cta.strip().endswith("?"):
        raw_cta = raw_cta.strip() + " What is the biggest obstacle stopping you from building this into your business right now?"
    cf.cta = raw_cta

    if content_type == "article":
        cf.title = _extract_section(body, "Title")
        cf.key_takeaway = _extract_section(body, "Key Takeaway")
        cf.youtube_script = _extract_section(body, "YouTube Short Script")
        # Enforce engagement question in youtube script too
        if cf.youtube_script and "ENGAGEMENT" not in cf.youtube_script.upper() and "CTA" not in cf.youtube_script.upper():
            cf.youtube_script = cf.youtube_script.strip() + "\n\nENGAGEMENT:\nWhat would change in your business if you had a system doing this automatically?"

    # Fallback: if sections weren't found (old format), use raw body
    if not cf.hook and not cf.body:
        cf.body = body.strip()

    return cf


def parse_week_files(files: list[tuple[str, str]]) -> tuple[list, list]:
    """
    Parse a list of (filename, raw_text) tuples.
    Returns (posts, articles) sorted by day number.
    files: list of (filename, raw_text)
    """
    posts = []
    articles = []

    for filename, raw_text in files:
        cf = parse_content_file(filename, raw_text)
        if cf.is_article():
            articles.append(cf)
        else:
            posts.append(cf)

    posts.sort(key=lambda x: x.day)
    articles.sort(key=lambda x: x.day)
    return posts, articles

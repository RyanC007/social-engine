"""
LinkedIn post builder  - takes Manus-generated content (read from Drive)
and structures it as the pillar post. Brand images from Week 1 are attached.
All other platform content is derived from this post.
"""
from dataclasses import dataclass, field


@dataclass
class LinkedInPost:
    text: str
    topic: str
    hashtags: list[str] = field(default_factory=list)
    author_urn: str = ""
    brand_images: list[str] = field(default_factory=list)   # local file paths
    ryan_context: str = ""                                   # author knowledge base
    youtube_script: str = ""                                 # article YouTube Short script

    def with_hashtags(self, tags: list[str]) -> "LinkedInPost":
        self.hashtags = tags
        return self

    def formatted(self) -> str:
        """Full post text with hashtags appended."""
        body = self.text.strip()
        if self.hashtags:
            tag_line = " ".join(f"#{t.lstrip('#')}" for t in self.hashtags)
            body = f"{body}\n\n{tag_line}"
        return body

    def summary(self) -> str:
        """First 200 chars  - seed for repurposing other platforms."""
        return self.text[:200].strip()


def build_linkedin_post(
    content: str,
    topic: str,
    hashtags: list[str] = None,
    author_urn: str = "",
    brand_images: list[str] = None,
    ryan_context: str = "",
) -> LinkedInPost:
    """
    Structure the Manus-generated content into a LinkedInPost.

    content:      raw text from Google Drive (Manus output for current week).
    ryan_context: author knowledge base  - who Ryan is, his voice, expertise.
                  Used during review so the editor has full context.
    brand_images: local paths to Week 1 brand template images.
    """
    tags = hashtags if hashtags is not None else _infer_hashtags(topic)

    # If Ryan's knowledge context is available, prepend a voice note to guide
    # any manual edits  - it's not published, just visible during review.
    text = content.strip()

    return LinkedInPost(
        text=text,
        topic=topic,
        hashtags=tags,
        author_urn=author_urn,
        brand_images=brand_images or [],
        ryan_context=ryan_context,
    )


def _infer_hashtags(topic: str) -> list[str]:
    words = topic.lower().replace(",", "").split()
    return [w for w in words if len(w) > 3][:5]

"""
Blotato publisher using ClientConfig.
Mirrors publisher/blotato.py but is fully client-config-driven.

Payload structure per Blotato API spec (https://backend.blotato.com/v2):
  POST /posts expects:
    {
      "post": {
        "accountId": "...",
        "content": { "text": "...", "mediaUrls": [], "platform": "twitter" },
        "target": { "targetType": "twitter", ...platform-specific fields }
      },
      "scheduledTime": "ISO8601"   <-- ROOT level, NOT inside "post"
    }
"""
import requests
from typing import Optional
from engine.client_config import ClientConfig

YOUTUBE_SHORTS_TEMPLATE_DEFAULT = "5903fe43-514d-40ee-a060-0d6628c5f8fd"   # bare UUID
INSTAGRAM_QUOTE_TEMPLATE_DEFAULT = "9f4e66cd-b784-4c02-b2ce-e6d0765fd4c0"


def _headers(cfg: ClientConfig) -> dict:
    if not cfg.blotato_api_key:
        raise ValueError(f"BLOTATO API key missing for client '{cfg.slug}'")
    return {
        "blotato-api-key": cfg.blotato_api_key,
        "Content-Type": "application/json",
    }


def _post(cfg: ClientConfig, endpoint: str, payload: dict) -> dict:
    url = f"{cfg.blotato_base_url()}{endpoint}"
    resp = requests.post(url, headers=_headers(cfg), json=payload, timeout=30)
    if not resp.ok:
        raise requests.HTTPError(
            f"{resp.status_code} {resp.reason}  - {resp.text}", response=resp
        )
    return resp.json()


def _get(cfg: ClientConfig, endpoint: str) -> dict:
    url = f"{cfg.blotato_base_url()}{endpoint}"
    resp = requests.get(url, headers=_headers(cfg), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _build_payload(account_id: str, platform: str, text: str,
                   media_urls: list = None, target_extra: dict = None,
                   schedule_at: str = None) -> dict:
    """
    Build a correctly structured Blotato POST /posts payload.

    IMPORTANT per API spec:
      - content.platform and target.targetType must be the same value
      - scheduledTime is a ROOT-level field (sibling of "post"), NOT nested inside "post"
      - If scheduledTime is nested inside "post", it is silently ignored and post publishes immediately
    """
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "mediaUrls": media_urls or [],
                "platform": platform,
            },
            "target": {
                "targetType": platform,
                **(target_extra or {}),
            },
        }
    }
    # scheduledTime MUST be at root level  - never nest inside "post"
    if schedule_at:
        payload["scheduledTime"] = schedule_at
    return payload


# ---------------------------------------------------------------------------
# Platform publishers
# ---------------------------------------------------------------------------

def publish_linkedin(cfg: ClientConfig, text: str, media_urls: list = None,
                     schedule_at: str = None, page_key: str = None) -> dict:
    acct = cfg.accounts["linkedin"]
    target_extra = {}
    if page_key and page_key in cfg.linkedin_pages:
        target_extra["pageId"] = cfg.linkedin_pages[page_key]
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="linkedin",
        text=text,
        media_urls=media_urls,
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post(cfg, "/posts", payload)


def publish_x(cfg: ClientConfig, text: str, media_urls: list = None,
              schedule_at: str = None, thread_posts: list = None) -> dict:
    acct = cfg.accounts["x"]
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="twitter",
        text=text,
        media_urls=media_urls,
        schedule_at=schedule_at,
    )
    if thread_posts:
        payload["post"]["additionalPosts"] = [
            {"text": t, "mediaUrls": []} for t in thread_posts
        ]
    return _post(cfg, "/posts", payload)


def publish_threads(cfg: ClientConfig, text: str, media_urls: list = None,
                    schedule_at: str = None) -> dict:
    # Threads shares the Instagram account_id
    acct = cfg.accounts.get("threads") or cfg.accounts.get("instagram")
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="threads",
        text=text,
        media_urls=media_urls,
        schedule_at=schedule_at,
    )
    return _post(cfg, "/posts", payload)


def publish_instagram(cfg: ClientConfig, text: str, media_urls: list = None,
                      media_type: str = "reel", schedule_at: str = None) -> dict:
    acct = cfg.accounts["instagram"]
    target_extra = {
        "mediaType": media_type,
        "shareToFeed": True,
    }
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="instagram",
        text=text,
        media_urls=media_urls,
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post(cfg, "/posts", payload)


def publish_youtube_short(cfg: ClientConfig, text: str, video_url: str,
                          title: str = None, privacy: str = "public",
                          schedule_at: str = None) -> dict:
    acct = cfg.accounts["youtube"]
    short_title = title or text[:100].split("\n")[0].strip()
    target_extra = {
        "title": short_title,
        "privacyStatus": privacy,
        "shouldNotifySubscribers": True,
    }
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="youtube",
        text=text,
        media_urls=[video_url],
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post(cfg, "/posts", payload)


def publish_tiktok(cfg: ClientConfig, text: str, video_url: str,
                   schedule_at: str = None) -> dict:
    acct = cfg.accounts["tiktok"]
    target_extra = {
        "privacyLevel": "PUBLIC_TO_EVERYONE",
        "disabledComments": False,
        "disabledDuet": False,
        "disabledStitch": False,
        "isBrandedContent": False,
        "isYourBrand": False,
        "isAiGenerated": True,
    }
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="tiktok",
        text=text,
        media_urls=[video_url],
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post(cfg, "/posts", payload)


def publish_facebook(cfg: ClientConfig, text: str, page_key: str = None,
                     media_urls: list = None, schedule_at: str = None,
                     link: str = None) -> dict:
    acct = cfg.accounts["facebook"]
    page_key = page_key or next(iter(cfg.facebook_pages), None)
    page_id = cfg.facebook_pages.get(page_key) or acct.get("page_id")
    if not page_id:
        raise ValueError(f"No Facebook page ID found for client '{cfg.slug}'")
    target_extra = {"pageId": page_id}
    if link:
        target_extra["link"] = link
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="facebook",
        text=text,
        media_urls=media_urls,
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post(cfg, "/posts", payload)


# ---------------------------------------------------------------------------
# Visuals
# ---------------------------------------------------------------------------

def create_youtube_short_video(cfg: ClientConfig, script: str, topic: str) -> dict:
    template_id = cfg.visual_templates.get("youtube_shorts", YOUTUBE_SHORTS_TEMPLATE_DEFAULT)

    # Parse script into hook / insight / engagement sections
    # Supports both ENGAGEMENT: and CTA: labels for backwards compatibility
    lines = [l.strip() for l in script.split("\n") if l.strip()
             and not l.strip().startswith(("HOOK:", "INSIGHT:", "CTA:", "ENGAGEMENT:"))]
    hook = lines[0] if lines else topic
    insight = " ".join(lines[1:3]) if len(lines) > 1 else f"Here is what most people get wrong about {topic}."
    # Engagement question -- never a generic follow CTA
    engagement = lines[-1] if len(lines) > 2 and lines[-1].endswith("?") else (
        f"What would change in your business if you had a system doing this automatically?"
    )

    payload = {
        "templateId": template_id,
        "prompt": (
            f"Create a punchy 60-second vertical YouTube Short (9:16) about: {topic}. "
            f"Use voice: {cfg.video_voice()}. "
            f"Scene 1 hook: {hook}. "
            f"Scene 2 insight: {insight}. "
            f"Scene 3 engagement question: {engagement}. "
            f"Professional business/AI style. Dark modern visuals. Captions at bottom."
        ),
        "inputs": {
            "aspectRatio": "9:16",
            "enableVoiceover": True,
            "voiceName": cfg.video_voice(),
            "trimToVoiceover": True,
            "captionPosition": "bottom",
            "highlightColor": "#FFFF00",
        },
        "render": True,
    }
    return _post(cfg, "/videos/from-templates", payload)


def create_facebook_image(cfg: ClientConfig, topic: str, template_id: str) -> dict:
    """Generate a Facebook image using the day-based rotation."""
    website = cfg.website() or ""
    payload = {
        "templateId": template_id,
        "inputs": {
            "description": f"{topic}. Educational guide for business owners.",
            "footerText": f"{cfg.name} | {website}" if website else cfg.name,
        },
        "render": True,
    }
    return _post(cfg, "/videos/from-templates", payload)


def create_linkedin_image(cfg: ClientConfig, topic: str, template_id: str, hook: str = None) -> dict:
    """
    Generate a LinkedIn image using the given infographic template.
    template_id comes from the linkedin_image_rotation array in client config.
    hook: the post's opening hook text - used as the image headline so the
          visual matches the copy. Falls back to topic if not provided.
    """
    website = cfg.website() or ""
    footer = f"{cfg.name} | {website}" if website else cfg.name
    # Use the hook as the image description so the visual reflects the post.
    # Truncate to 150 chars to fit template headline fields cleanly.
    description = (hook.strip()[:150] if hook else None) or f"{topic}. Key insights for business owners."
    payload = {
        "templateId": template_id,
        "inputs": {
            "description": description,
            "footerText": footer,
        },
        "render": True,
    }
    return _post(cfg, "/videos/from-templates", payload)


def create_instagram_image(cfg: ClientConfig, quotes: list, topic: str) -> dict:
    """
    Generate a multi-slide Instagram quote card carousel.
    quotes: list of short punchy strings  - each becomes one slide.
    """
    template_id = cfg.visual_templates.get("instagram_quote", INSTAGRAM_QUOTE_TEMPLATE_DEFAULT)
    highlighter = cfg.visual_templates.get("instagram_quote_highlighter", "#F97316")
    paper = cfg.visual_templates.get("instagram_quote_paper", "White paper")

    payload = {
        "templateId": template_id,
        "inputs": {
            "title": cfg.name,
            "quotes": quotes[:6],   # max 6 slides
            "highlighterColor": highlighter,
            "paperBackground": paper,
            "aspectRatio": "4:5",
        },
        "render": True,
    }
    return _post(cfg, "/videos/from-templates", payload)


def get_visual_status(cfg: ClientConfig, creation_id: str) -> dict:
    return _get(cfg, f"/videos/creations/{creation_id}")

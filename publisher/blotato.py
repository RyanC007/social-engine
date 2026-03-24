"""
Blotato publisher  - posts to LinkedIn, X, Instagram, YouTube, and Facebook
via the Blotato REST API (https://backend.blotato.com/v2).

Auth:   blotato-api-key header
Docs:   help.blotato.com/api

Workflow:
  LinkedIn is the pillar post. All other platforms are repurposed from it.
  YouTube Shorts requires a video URL (generate one via Blotato visuals or
  provide externally). If no video URL is available the Short is skipped.
"""
import requests
import config
from content.linkedin_builder import LinkedInPost
from content.repurposer import PlatformPost


# Visual template IDs
YOUTUBE_SHORTS_TEMPLATE = "5903fe43-514d-40ee-a060-0d6628c5f8fd"   # bare UUID required
INSTAGRAM_QUOTE_TEMPLATE = "9f4e66cd-b784-4c02-b2ce-e6d0765fd4c0"   # single quote on solid background  - one image


def _headers() -> dict:
    if not config.BLOTATO_API_KEY:
        raise ValueError("BLOTATO_API_KEY is not set in .env")
    return {
        "blotato-api-key": config.BLOTATO_API_KEY,
        "Content-Type": "application/json",
    }


def _post(endpoint: str, payload: dict) -> dict:
    url = f"{config.BLOTATO_BASE_URL}{endpoint}"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _get(endpoint: str) -> dict:
    url = f"{config.BLOTATO_BASE_URL}{endpoint}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _build_payload(account_id: str, platform: str, text: str,
                   media_urls: list = None, target_extra: dict = None,
                   schedule_at: str = None) -> dict:
    """
    Build a correctly structured Blotato POST /posts payload.

    Per the API spec:
      - "post" wraps accountId, content, and target
      - content holds: text, mediaUrls, platform
      - target holds: targetType + any platform-specific fields (e.g. pageId)
      - scheduledTime is a ROOT-LEVEL field, sibling of "post"  - NOT nested inside
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
    # scheduledTime must be at root level  - nested inside "post" is silently ignored
    if schedule_at:
        payload["scheduledTime"] = schedule_at
    return payload


# ---------------------------------------------------------------------------
# Platform publishers
# ---------------------------------------------------------------------------

def publish_linkedin(post: LinkedInPost, schedule_at: str = None, as_company: str = None) -> dict:
    """
    Publish to LinkedIn.
    as_company: key from config.LINKEDIN_PAGES to post as a company page,
                e.g. "ready_plan_grow". Omit to post as Ryan personally.
    """
    acct = config.BLOTATO_ACCOUNTS["linkedin"]
    target_extra = {}
    if as_company and as_company in config.LINKEDIN_PAGES:
        target_extra["pageId"] = config.LINKEDIN_PAGES[as_company]

    payload = _build_payload(
        account_id=acct["account_id"],
        platform="linkedin",
        text=post.formatted(),
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post("/posts", payload)


def publish_x(post: PlatformPost, schedule_at: str = None) -> dict:
    """Publish to X (Twitter)."""
    acct = config.BLOTATO_ACCOUNTS["x"]
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="twitter",
        text=post.formatted(),
        schedule_at=schedule_at,
    )
    return _post("/posts", payload)


def publish_threads(post: PlatformPost, schedule_at: str = None) -> dict:
    """Publish to Threads."""
    acct = config.BLOTATO_ACCOUNTS.get("threads") or config.BLOTATO_ACCOUNTS.get("instagram")
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="threads",
        text=post.formatted(),
        schedule_at=schedule_at,
    )
    return _post("/posts", payload)


def publish_instagram(post: PlatformPost, media_urls: list[str] = None,
                      media_type: str = "reel", schedule_at: str = None) -> dict:
    """
    Publish to Instagram.
    media_type: "reel" (default) or "story"
    media_urls: list of public image/video URLs. Pass [] for caption-only (rarely supported).
    """
    acct = config.BLOTATO_ACCOUNTS["instagram"]
    target_extra = {
        "mediaType": media_type,
        "shareToFeed": True,
    }
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="instagram",
        text=post.formatted(),
        media_urls=media_urls or [],
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post("/posts", payload)


def publish_youtube_short(post: PlatformPost, video_url: str,
                          title: str = None, privacy: str = "public",
                          schedule_at: str = None) -> dict:
    """
    Publish a YouTube Short.
    video_url:  publicly accessible video URL (required  - YouTube needs a video).
    title:      video title (defaults to first 100 chars of the post text).
    privacy:    "public" | "private" | "unlisted"
    """
    acct = config.BLOTATO_ACCOUNTS["youtube"]
    short_title = title or post.text[:100].split("\n")[0].strip()
    target_extra = {
        "title": short_title,
        "privacyStatus": privacy,
        "shouldNotifySubscribers": True,
    }
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="youtube",
        text=post.formatted(),
        media_urls=[video_url],
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post("/posts", payload)


def publish_facebook(post: PlatformPost, page_key: str = "ready_plan_grow",
                     schedule_at: str = None) -> dict:
    """
    Publish to a Facebook page.
    page_key: key from config.FACEBOOK_PAGES. Defaults to Ready Plan Grow.
    """
    acct = config.BLOTATO_ACCOUNTS["facebook"]
    page_id = config.FACEBOOK_PAGES.get(page_key)
    if not page_id:
        raise ValueError(f"Unknown Facebook page key: {page_key}")
    target_extra = {"pageId": page_id}
    payload = _build_payload(
        account_id=acct["account_id"],
        platform="facebook",
        text=post.formatted(),
        target_extra=target_extra,
        schedule_at=schedule_at,
    )
    return _post("/posts", payload)


# ---------------------------------------------------------------------------
# Visual generation (Blotato AI)
# ---------------------------------------------------------------------------

def create_youtube_shorts_video(script: str, topic: str) -> dict:
    """
    Generate a YouTube Short video via Blotato AI video templates.
    Returns the creation response  - poll get_visual_status for the
    final mediaUrl before calling publish_youtube_short().
    """
    payload = {
        "templateId": YOUTUBE_SHORTS_TEMPLATE,
        "prompt": f"Create a 60-second YouTube Short about: {topic}. Script: {script}",
        "inputs": {},   # let AI fill inputs from prompt
        "render": True,
    }
    return _post("/videos/from-templates", payload)


def get_visual_status(creation_id: str) -> dict:
    """Poll the status of a Blotato visual creation."""
    return _get(f"/videos/creations/{creation_id}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def publish_all(
    linkedin_post: LinkedInPost,
    platform_posts: dict,
    schedule_at: str = None,
    youtube_video_url: str = None,
    linkedin_as_company: str = None,
) -> dict:
    """
    Publish LinkedIn pillar + all approved repurposed posts.

    platform_posts: dict of platform -> PlatformPost (from repurposer).
                    Only platforms present in this dict are published.
    youtube_video_url: if provided, publishes YouTube Short with this video.
                       If None, YouTube Short is skipped (script still reviewed).
    linkedin_as_company: key from config.LINKEDIN_PAGES to post as company page.
    """
    results = {}

    if linkedin_post.text:
        print("  LinkedIn...")
        results["linkedin"] = publish_linkedin(
            linkedin_post,
            schedule_at=schedule_at,
            as_company=linkedin_as_company,
        )

    platform_map = {
        "x":        lambda p: publish_x(p, schedule_at=schedule_at),
        "threads":  lambda p: publish_threads(p, schedule_at=schedule_at),
        "instagram": lambda p: publish_instagram(p, schedule_at=schedule_at),
        "facebook":  lambda p: publish_facebook(p, schedule_at=schedule_at),
    }

    for platform, post in platform_posts.items():
        if platform == "youtube_shorts":
            if youtube_video_url:
                print("  YouTube Shorts...")
                results["youtube_shorts"] = publish_youtube_short(
                    post, video_url=youtube_video_url, schedule_at=schedule_at
                )
            else:
                print("  YouTube Shorts skipped  - no video URL provided.")
                print("  Use Blotato visuals (or create_youtube_shorts_video()) to generate one.")
            continue

        handler = platform_map.get(platform)
        if handler:
            print(f"  {platform.upper().replace('_', ' ')}...")
            results[platform] = handler(post)
        else:
            print(f"  {platform} not supported  - skipping.")

    return results

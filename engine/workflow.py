"""
Orchestrates the full content publishing workflow for any client.

This is the engine that main.py and mcp_server.py both call.
It is completely client-config-driven - no globals from config.py.
"""
import time
from typing import Optional
from engine.client_config import ClientConfig, load_client
from engine.drive import (
 list_week_folders, get_current_week_folder, get_week_folder_by_name,
 load_week_content_files, get_client_knowledge, get_brand_images,
)
from knowledge_base.content_parser import parse_week_files, ContentFile
from content.linkedin_builder import build_linkedin_post
from content.repurposer import repurpose_all
from engine.publisher import (
 publish_linkedin, publish_x, publish_threads, publish_instagram,
 publish_youtube_short, publish_tiktok, publish_facebook,
 create_youtube_short_video, create_linkedin_image, create_facebook_image,
 create_instagram_image, get_visual_status,
)

# How long to wait for Blotato video generation before giving up (seconds)
YOUTUBE_GENERATION_TIMEOUT = 300
YOUTUBE_POLL_INTERVAL = 10


def get_week_summary(client_slug: str, week: str = None) -> dict:
 """
 Return a summary of this week's content (posts + articles) without publishing.
 Used by MCP tools for preview.
 """
 cfg = load_client(client_slug)
 folder = (
 get_week_folder_by_name(cfg, week) if week
 else get_current_week_folder(cfg)
 )
 if not folder:
 return {"error": "No week folder found"}

 raw_files = load_week_content_files(cfg, folder)
 if not raw_files:
 return {"error": "No content files found in this week's folder"}

 posts, articles = parse_week_files(raw_files)
 return {
 "week": folder["name"],
 "posts": [{"day": p.day, "topic": p.topic, "platforms": p.platforms} for p in posts],
 "articles": [{"day": a.day, "topic": a.topic, "platforms": a.platforms} for a in articles],
 }


def _generate_facebook_image(cfg: ClientConfig, pillar) -> str | None:
 """Auto-generate a Facebook image using the day-based rotation."""
 rotation = cfg.visual_templates.get("facebook_image_rotation", [])
 if not rotation:
 return None
 template = rotation[pillar.day % len(rotation)]
 try:
 creation = create_facebook_image(cfg, topic=pillar.topic, template_id=template["id"])
 creation_id = creation.get("item", {}).get("id") or creation.get("id")
 if not creation_id:
 return None
 print(f" Generating Facebook {template.get('name')} image (id: {creation_id})...")
 deadline = time.time() + YOUTUBE_GENERATION_TIMEOUT
 while time.time() < deadline:
 status_resp = get_visual_status(cfg, creation_id)
 item = status_resp.get("item", status_resp)
 status = item.get("status", "")
 if status == "done":
 urls = item.get("imageUrls") or []
 return urls[0] if urls else item.get("mediaUrl")
 if status == "creation-from-template-failed":
 return None
 time.sleep(YOUTUBE_POLL_INTERVAL)
 except Exception as e:
 print(f" Facebook image generation failed: {e}")
 return None


def _generate_linkedin_image(cfg: ClientConfig, pillar) -> str | None:
 """
 Auto-generate a LinkedIn image using the day-based rotation.
 Returns imageUrls[0] on success, or None on failure/timeout.
 """
 rotation = cfg.visual_templates.get("linkedin_image_rotation", [])
 if not rotation:
 return None

 template = rotation[pillar.day % len(rotation)]
 template_id = template["id"]
 template_name = template.get("name", template_id)

 try:
 # Pass the hook text so the image headline matches the post copy
 hook_text = getattr(pillar, "hook", None) or pillar.topic
 creation = create_linkedin_image(cfg, topic=pillar.topic, template_id=template_id, hook=hook_text)
 creation_id = creation.get("item", {}).get("id") or creation.get("id")
 if not creation_id:
 return None

 print(f" Generating {template_name} image (id: {creation_id})...")
 deadline = time.time() + YOUTUBE_GENERATION_TIMEOUT
 while time.time() < deadline:
 status_resp = get_visual_status(cfg, creation_id)
 item = status_resp.get("item", status_resp)
 status = item.get("status", "")
 if status == "done":
 urls = item.get("imageUrls") or []
 return urls[0] if urls else item.get("mediaUrl")
 if status == "creation-from-template-failed":
 return None
 time.sleep(YOUTUBE_POLL_INTERVAL)
 except Exception as e:
 print(f" LinkedIn image generation failed: {e}")
 return None


def _generate_youtube_video(cfg: ClientConfig, post, pillar) -> str | None:
 """
 Auto-generate a YouTube Short video via Blotato visuals.
 Returns the mediaUrl on success, or None on failure/timeout.

 Script priority:
 1. pillar.youtube_script (from ## YouTube Short Script section in article)
 2. post.video_prompt (structured HOOK/INSIGHT/ENGAGEMENT string from repurposer)
 3. pillar.topic (bare fallback)
 The video_prompt is used for Blotato's generation API only and never published.
 """
 script = getattr(pillar, "youtube_script", None) or getattr(post, "video_prompt", None) or pillar.topic
 try:
 creation = create_youtube_short_video(cfg, script=script, topic=pillar.topic)
 creation_id = creation.get("item", {}).get("id") or creation.get("id")
 if not creation_id:
 return None

 deadline = time.time() + YOUTUBE_GENERATION_TIMEOUT
 while time.time() < deadline:
 status_resp = get_visual_status(cfg, creation_id)
 item = status_resp.get("item", status_resp)
 status = item.get("status", "")
 if status == "done":
 return item.get("mediaUrl") or (item.get("imageUrls") or [None])[0]
 if status in ("creation-from-template-failed", "error"):
 print(f" Video generation failed with status: {status}")
 return None
 time.sleep(YOUTUBE_POLL_INTERVAL)
 print(f" Video generation timed out after {YOUTUBE_GENERATION_TIMEOUT}s")
 except Exception as e:
 print(f" Video generation error: {e}")
 return None


def _extract_ig_quotes(pillar) -> list:
 """
 Pull 3-5 short punchy lines from the pillar to use as quote card slides.
 Each slide should be a single tight sentence - no more than ~120 chars.
 Hashtag-heavy lines are excluded (Blotato template API rejects them).
 """
 lines = [l.strip() for l in pillar.raw_body.split("\n")
 if l.strip() and not l.strip().startswith(("#", "##", "---"))]
 quotes = []
 for line in lines:
 line = line.lstrip("*-\u2192\u2022").strip()
 # Skip lines where more than half the words are hashtags
 words = line.split()
 if words and sum(1 for w in words if w.startswith('#')) / len(words) > 0.4:
 continue
 # Strip any trailing hashtag clusters from the line
 clean_words = [w for w in words if not w.startswith('#')]
 line = ' '.join(clean_words).strip()
 if 20 <= len(line) <= 120:
 quotes.append(line)
 if len(quotes) >= 5:
 break
 # Always start with the topic as the first slide if we have room
 if pillar.topic and len(pillar.topic) <= 80:
 quotes.insert(0, pillar.topic)
 return quotes[:6] if quotes else [pillar.topic]


def _publish_instagram_with_quotes(cfg, post, pillar, schedule_at):
 """Generate multi-slide quote card then publish to Instagram."""
 quotes = _extract_ig_quotes(pillar)
 try:
 creation = create_instagram_image(cfg, quotes=quotes, topic=pillar.topic)
 creation_id = creation.get("item", {}).get("id") or creation.get("id")
 if creation_id:
 deadline = time.time() + YOUTUBE_GENERATION_TIMEOUT
 while time.time() < deadline:
 status_resp = get_visual_status(cfg, creation_id)
 item = status_resp.get("item", status_resp)
 status = item.get("status", "")
 if status == "done":
 image_urls = item.get("imageUrls") or []
 media_urls = image_urls[:1] # Instagram single image from carousel
 return publish_instagram(cfg, text=post.formatted(),
 media_urls=media_urls, schedule_at=schedule_at)
 if status == "creation-from-template-failed":
 break
 time.sleep(YOUTUBE_POLL_INTERVAL)
 except Exception as e:
 print(f" Instagram image generation failed: {e}")
 # Fallback - publish caption only
 return publish_instagram(cfg, text=post.formatted(), schedule_at=schedule_at)


def _publish_facebook_with_image(cfg, post, pillar, schedule_at, website):
 image_url = _generate_facebook_image(cfg, pillar)
 return publish_facebook(
 cfg,
 text=post.formatted(),
 page_key=cfg.default_facebook_page(),
 media_urls=[image_url] if image_url else None,
 schedule_at=schedule_at,
 )


def run_publish(
 client_slug: str,
 pillar_day: int,
 week: str = None,
 schedule_at: str = None,
 youtube_video_url: str = None,
 linkedin_as_company: str = None,
 platforms: list = None,
 dry_run: bool = False,
) -> dict:
 """
 Full publish run for a client.

 pillar_day: day number of the pillar content (post or article)
 week: week folder name e.g. "Week-2" (defaults to latest)
 schedule_at: ISO 8601 datetime to schedule posts (omit to publish immediately)
 youtube_video_url: pre-rendered video URL; if omitted, auto-generates via Blotato
 linkedin_as_company: key from client's linkedin_pages to post as company
 platforms: subset of platforms to publish to (default: all in frontmatter)
 dry_run: build everything but don't publish
 """
 cfg = load_client(client_slug)
 folder = (
 get_week_folder_by_name(cfg, week) if week
 else get_current_week_folder(cfg)
 )
 if not folder:
 return {"error": "No week folder found"}

 raw_files = load_week_content_files(cfg, folder)
 if not raw_files:
 return {"error": "No content files found"}

 posts, articles = parse_week_files(raw_files)
 all_content = sorted(posts + articles, key=lambda x: x.day)

 pillar = next((c for c in all_content if c.day == pillar_day), None)
 if not pillar:
 available = [c.day for c in all_content]
 return {"error": f"Day {pillar_day} not found. Available days: {available}"}

 client_knowledge = get_client_knowledge(cfg)
 brand_images = get_brand_images(cfg)

 # Use post hashtags from Drive file; fall back to client brand defaults
 hashtags = pillar.hashtags if pillar.hashtags else cfg.default_hashtags()

 linkedin_post = build_linkedin_post(
 content=pillar.linkedin_text(),
 topic=pillar.topic,
 hashtags=hashtags,
 author_urn="",
 brand_images=brand_images,
 ryan_context=client_knowledge,
 )

 if pillar.is_article() and pillar.youtube_script:
 linkedin_post.youtube_script = pillar.youtube_script

 all_platform_posts = repurpose_all(linkedin_post, tiktok_handle=cfg.tiktok_handle(), website=cfg.website())
 target_platforms = set(platforms) if platforms else set(pillar.platforms)

 platform_posts = {
 k: v for k, v in all_platform_posts.items()
 if k in target_platforms
 }

 if dry_run:
 return {
 "dry_run": True,
 "week": folder["name"],
 "pillar": {"day": pillar.day, "topic": pillar.topic, "type": pillar.content_type},
 "linkedin_text": linkedin_post.formatted()[:300] + "...",
 "platforms": {
 p: post.formatted()[:200] + "..." for p, post in platform_posts.items()
 },
 }

 results = {}

 # LinkedIn - auto-generate rotated image (whiteboard/newspaper/etc by day)
 if "linkedin" in target_platforms and linkedin_post.text:
 image_url = _generate_linkedin_image(cfg, pillar)
 media_urls = [image_url] if image_url else (brand_images[:1] if brand_images else [])
 try:
 results["linkedin"] = publish_linkedin(
 cfg,
 text=linkedin_post.formatted(),
 media_urls=media_urls,
 schedule_at=schedule_at,
 page_key=linkedin_as_company,
 )
 except Exception as e:
 results["linkedin"] = {"error": str(e)}

 website = cfg.website()
 platform_map = {
 "x": lambda p: publish_x(cfg, text=p.formatted(), schedule_at=schedule_at, thread_posts=p.thread_posts or None),
 "instagram": lambda p: _publish_instagram_with_quotes(cfg, p, pillar, schedule_at),
 "facebook": lambda p: _publish_facebook_with_image(cfg, p, pillar, schedule_at, website),
 }

 # Generate video once - shared by both YouTube Shorts and TikTok
 needs_video = any(p in target_platforms for p in ("youtube_shorts", "tiktok"))
 shared_video_url = None
 if needs_video:
 shared_video_url = youtube_video_url
 if not shared_video_url:
 yt_post = platform_posts.get("youtube_shorts") or platform_posts.get("tiktok")
 if yt_post:
 shared_video_url = _generate_youtube_video(cfg, yt_post, pillar)

 for platform, post in platform_posts.items():
 if platform == "youtube_shorts":
 if shared_video_url:
 try:
 results["youtube_shorts"] = publish_youtube_short(
 cfg, text=post.formatted(), video_url=shared_video_url,
 schedule_at=schedule_at,
 )
 except Exception as e:
 results["youtube_shorts"] = {"error": str(e)}
 else:
 results["youtube_shorts"] = {"skipped": "Video generation failed or timed out"}
 continue

 if platform == "tiktok":
 if shared_video_url:
 try:
 results["tiktok"] = publish_tiktok(
 cfg, text=post.formatted(), video_url=shared_video_url,
 schedule_at=schedule_at,
 )
 except Exception as e:
 results["tiktok"] = {"error": str(e)}
 else:
 results["tiktok"] = {"skipped": "Video generation failed or timed out"}
 continue

 handler = platform_map.get(platform)
 if handler:
 try:
 results[platform] = handler(post)
 except Exception as e:
 results[platform] = {"error": str(e)}

 return {
 "week": folder["name"],
 "pillar": {"day": pillar.day, "topic": pillar.topic},
 "results": results,
 }
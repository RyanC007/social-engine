#!/usr/bin/env python3
"""
Ryan Social Engine  - CLI entry point.

Workflow:
  1. Read current week's content from Google Drive (Manus drops it there)
  2. Parse posts vs articles, show menu to pick the LinkedIn pillar
  3. Pull Ryan's knowledge base + Week 1 brand images
  4. Build LinkedIn pillar post (from selected post or article)
  5. Review & edit each platform post interactively
  6. Publish all approved posts via Blotato

Usage:
    python main.py --week "Week-2"
    python main.py --week "Week-2" --schedule "2026-03-20T09:00:00Z"
    python main.py --week "Week-2" --dry-run
    python main.py --week "Week-2" --linkedin-as-company ready_plan_grow
    python main.py --week "Week-2" --youtube-video-url https://...
"""
import argparse
import tempfile
import os
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

import config
from knowledge_base.google_drive import (
    get_brand_images, get_current_week_folder, get_client_knowledge,
    list_week_folders, load_week_content_files,
)
from knowledge_base.content_parser import parse_week_files, ContentFile
from content.linkedin_builder import build_linkedin_post, LinkedInPost
from content.repurposer import repurpose_all
from content.hook_selector import suggest_hooks, format_hook_menu, apply_hook
from publisher.blotato import publish_all

console = Console()

PLATFORM_COLORS = {
    "linkedin":      "blue",
    "x":             "cyan",
    "instagram":     "magenta",
    "threads":       "yellow",
    "youtube_shorts": "red",
}


def edit_in_terminal(current_text: str, platform: str) -> str:
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix=f"{platform}_post_", delete=False
    ) as f:
        f.write(current_text)
        tmp_path = f.name
    subprocess.call([editor, tmp_path])
    with open(tmp_path, "r") as f:
        updated = f.read().strip()
    os.unlink(tmp_path)
    return updated


def review_post(text: str, title: str, platform: str, char_count: bool = True,
                content_type: str = "post") -> tuple:
    color = PLATFORM_COLORS.get(platform, "white")
    while True:
        subtitle = f"{len(text)} chars" if char_count else ""
        console.print(Panel(
            text,
            title=f"[bold]{title}[/bold]",
            border_style=color,
            subtitle=subtitle,
        ))
        choice = Prompt.ask(
            f"\n[bold]{title}[/bold]  - approve / edit / hook / skip?",
            choices=["approve", "edit", "hook", "skip"],
            default="approve",
        )
        if choice == "approve":
            console.print(f"[green]✓ {title} approved[/green]")
            return text, True
        elif choice == "edit":
            text = edit_in_terminal(text, platform)
            console.print("[green]✓ Updated[/green]")
        elif choice == "hook":
            # Show viral hook suggestions for this platform
            hooks = suggest_hooks(platform=platform, content_type=content_type, n=5)
            console.print(f"\n[bold yellow]Viral hooks for {platform.upper()}:[/bold yellow]")
            console.print(format_hook_menu(hooks))
            hook_choice = Prompt.ask(
                "Pick a hook (1-5) or press Enter to skip",
                default="0",
            )
            if hook_choice.isdigit() and 1 <= int(hook_choice) <= len(hooks):
                selected_hook = hooks[int(hook_choice) - 1]
                text = apply_hook(selected_hook, text)
                console.print(f"[green]✓ Hook applied[/green]")
        elif choice == "skip":
            console.print(f"[yellow]{title} skipped[/yellow]")
            return text, False


def pick_pillar(posts: list, articles: list) -> ContentFile:
    """Show a menu of posts and articles and let Ryan pick the LinkedIn pillar."""

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Type", width=10)
    table.add_column("Day", width=5)
    table.add_column("Topic")
    table.add_column("Platforms", style="dim")

    all_files = sorted(posts + articles, key=lambda x: x.day)
    for i, cf in enumerate(all_files):
        type_label = "[blue]ARTICLE[/blue]" if cf.is_article() else "[green]POST[/green]"
        table.add_row(
            str(i + 1),
            type_label,
            str(cf.day),
            cf.topic,
            ", ".join(cf.platforms),
        )

    console.print(table)
    choice = Prompt.ask(
        "\nWhich becomes the [bold blue]LinkedIn pillar[/bold blue]?",
        choices=[str(i + 1) for i in range(len(all_files))],
        default="1",
    )
    selected = all_files[int(choice) - 1]
    console.print(f"[green]✓[/green] Pillar: [bold]{selected.display_label()}[/bold]\n")
    return selected


def run(week: str = None, schedule_at: str = None, dry_run: bool = False,
        youtube_video_url: str = None, linkedin_as_company: str = None):

    console.rule("[bold blue]Ryan Social Engine")

    # ── Step 1: Resolve week folder ──────────────────────────────────────────
    if week:
        all_folders = list_week_folders()
        current_folder = next(
            (f for f in all_folders if f["name"].lower() == week.lower()), None
        )
        if not current_folder:
            available = ", ".join(f["name"] for f in all_folders)
            console.print(f"[red]Week '{week}' not found. Available: {available}[/red]")
            return
    else:
        current_folder = get_current_week_folder()

    week_label = current_folder["name"] if current_folder else "Unknown Week"
    console.print(f"\n[yellow]1/5[/yellow] Loading [bold]{week_label}[/bold] from Google Drive...")

    raw_files = load_week_content_files(current_folder)
    if not raw_files:
        console.print("[red]No content files found. Has Manus dropped the files in yet?[/red]")
        return

    posts, articles = parse_week_files(raw_files)
    console.print(
        f"[green]✓[/green] Found [bold]{len(posts)}[/bold] post(s) "
        f"and [bold]{len(articles)}[/bold] article(s)"
    )

    # ── Step 2: Pick LinkedIn pillar ─────────────────────────────────────────
    console.print(f"\n[yellow]2/5[/yellow] Select the [bold]LinkedIn pillar[/bold]\n")
    pillar = pick_pillar(posts, articles)

    # ── Step 3: Load Ryan's knowledge base ───────────────────────────────────
    console.print("[yellow]3/5[/yellow] Loading Ryan's knowledge base...")
    ryan_context = get_client_knowledge()
    if ryan_context:
        console.print(f"[green]✓[/green] Knowledge base: {len(ryan_context)} chars")
    else:
        console.print("[dim]No author knowledge found  - continuing without it[/dim]")

    # Brand images from Week 1
    brand_images = get_brand_images()
    if brand_images:
        console.print(f"[green]✓[/green] {len(brand_images)} brand image(s) loaded")

    # ── Step 4: Build & review LinkedIn post ─────────────────────────────────
    console.print(f"\n[yellow]4/5[/yellow] Building LinkedIn pillar post\n")
    linkedin_post = build_linkedin_post(
        content=pillar.linkedin_text(),
        topic=pillar.topic,
        hashtags=pillar.hashtags or None,
        author_urn=config.LINKEDIN_AUTHOR_URN or "",
        brand_images=brand_images,
        ryan_context=ryan_context,
    )

    li_text, li_approved = review_post(
        linkedin_post.formatted(), "LinkedIn Pillar Post", "linkedin"
    )
    if li_approved:
        linkedin_post.text = li_text
    else:
        linkedin_post.text = ""

    # ── Step 5: Repurpose & review each platform ─────────────────────────────
    # Only repurpose to platforms listed in the pillar's frontmatter
    target_platforms = set(pillar.platforms)

    # YouTube Shorts: use article's built-in script if available
    if pillar.is_article() and pillar.youtube_script:
        linkedin_post.youtube_script = pillar.youtube_script

    console.print(f"\n[yellow]5/5[/yellow] Repurposing for: {', '.join(target_platforms)}\n")
    all_platform_posts = repurpose_all(linkedin_post)

    # Filter to only the platforms Manus flagged for this piece
    platform_posts = {
        k: v for k, v in all_platform_posts.items()
        if k in target_platforms or
        (k == "youtube_shorts" and "youtube_shorts" in target_platforms)
    }

    approved_posts = {}
    for platform, post in platform_posts.items():
        label = platform.upper().replace("_", " ")
        text, ok = review_post(post.formatted(), label, platform)
        if ok:
            post.text = text
            approved_posts[platform] = post

    if not li_approved and not approved_posts:
        console.print("\n[red]Nothing approved  - exiting.[/red]")
        return

    if dry_run:
        console.print("\n[bold yellow]Dry run  - nothing published.[/bold yellow]")
        return

    # ── Confirm & publish ────────────────────────────────────────────────────
    platforms_ready = (["linkedin"] if li_approved else []) + list(approved_posts.keys())
    console.print(f"\nReady to publish to: [bold]{', '.join(platforms_ready)}[/bold]")
    if schedule_at:
        console.print(f"Scheduled for: [bold]{schedule_at}[/bold]")

    if not Confirm.ask("\nPublish now?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    console.print("\n[bold green]Publishing via Blotato...[/bold green]")
    results = publish_all(
        linkedin_post=linkedin_post,
        platform_posts=approved_posts,
        schedule_at=schedule_at,
        youtube_video_url=youtube_video_url,
        linkedin_as_company=linkedin_as_company,
    )

    console.print("\n[bold green]✓ All done![/bold green]")
    for platform, result in results.items():
        console.print(f"  {platform}: {result}")


def main():
    parser = argparse.ArgumentParser(description="Social Engine CLI")
    parser.add_argument("--client", default="your_client",
                        help="Client slug to run for (default: ryan). "
                             "Loads from clients/{slug}.json")
    parser.add_argument("--week", default=None,
                        help="Week folder to process e.g. 'Week-2' (defaults to latest)")
    parser.add_argument("--schedule", default=None,
                        help="ISO 8601 datetime to schedule posts e.g. 2026-03-20T09:00:00Z")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview all posts without publishing")
    parser.add_argument("--youtube-video-url", default=None,
                        help="Public video URL for YouTube Short")
    parser.add_argument("--linkedin-as-company", default=None,
                        help="Post LinkedIn as company page: your_company_page")
    args = parser.parse_args()

    run(
        week=args.week,
        schedule_at=args.schedule,
        dry_run=args.dry_run,
        youtube_video_url=args.youtube_video_url,
        linkedin_as_company=args.linkedin_as_company,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Automated daily publisher for the Social Engine.

Reads the chronologically ordered week folders from Drive, tracks which
day was last published in a per-client state file, and publishes the next
day in sequence each time it runs.

Usage:
    python auto_publish.py                        # publish next day (defaults to ryan)
    python auto_publish.py --client marcela       # publish for [CLIENT NAME]'s pipeline
    python auto_publish.py --dry-run              # preview only
    python auto_publish.py --reset                # clear state for this client
    python auto_publish.py --status               # show what would run next
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from engine.client_config import load_client
from engine.drive import list_week_folders, load_week_content_files
from engine.workflow import run_publish
from knowledge_base.content_parser import parse_week_files

# Per-client state files live in .state/ directory
STATE_DIR = Path(__file__).parent / ".state"
STATE_DIR.mkdir(exist_ok=True)


def _state_file(client_slug: str) -> Path:
    return STATE_DIR / f".publish_state_{client_slug}.json"


def _log_file(client_slug: str) -> Path:
    return STATE_DIR / f".publish_log_{client_slug}.jsonl"


def load_state(client_slug: str) -> dict:
    sf = _state_file(client_slug)
    if sf.exists():
        with open(sf) as f:
            return json.load(f)
    return {"week": None, "last_day": None}


def save_state(client_slug: str, week: str, day: int):
    with open(_state_file(client_slug), "w") as f:
        json.dump({"week": week, "last_day": day}, f)


def log_publish(client_slug: str, week: str, day: int, topic: str, result: dict):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "client": client_slug,
        "week": week,
        "day": day,
        "topic": topic,
        "result": result,
    }
    with open(_log_file(client_slug), "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_next_content(cfg, client_slug: str):
    """
    Find the next content day to publish.
    Returns (folder, content_item) or (None, None) if nothing left.
    """
    state = load_state(client_slug)
    week_folders = list_week_folders(cfg)

    if not week_folders:
        return None, None

    # Find starting folder -- either current state's week or the first one
    start_folder_idx = 0
    if state["week"]:
        for i, f in enumerate(week_folders):
            if f["name"] == state["week"]:
                start_folder_idx = i
                break

    # Search from current week forward
    for folder in week_folders[start_folder_idx:]:
        raw_files = load_week_content_files(cfg, folder)
        if not raw_files:
            continue

        posts, articles = parse_week_files(raw_files)
        all_content = sorted(posts + articles, key=lambda x: x.day)

        if not all_content:
            continue

        # If same week as state, find the next day after last_day
        if folder["name"] == state["week"] and state["last_day"] is not None:
            remaining = [c for c in all_content if c.day > state["last_day"]]
        else:
            # New week -- start from day 1
            remaining = all_content

        if remaining:
            return folder, remaining[0]

    return None, None


def main():
    parser = argparse.ArgumentParser(description="Automated daily publisher")
    parser.add_argument("--client", default="your_client_slug",
                        help="Client slug to run for (default: ryan). Loads from clients/{slug}.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview without publishing")
    parser.add_argument("--reset", action="store_true", help="Clear publish state for this client")
    parser.add_argument("--status", action="store_true", help="Show next scheduled content")
    args = parser.parse_args()

    client_slug = args.client

    if args.reset:
        sf = _state_file(client_slug)
        if sf.exists():
            sf.unlink()
        print(f"State cleared for client: {client_slug}")
        return

    cfg = load_client(client_slug)
    folder, content = get_next_content(cfg, client_slug)

    if not folder or not content:
        print(f"Nothing left to publish for '{client_slug}' -- all content for all weeks is done.")
        return

    print(f"[{client_slug}] Next: [{folder['name']}] Day {content.day} -- {content.topic}")
    print(f"Platforms: {', '.join(content.platforms)}")

    if args.status:
        state = load_state(client_slug)
        print(f"\nCurrent state: week={state['week']}, last_day={state['last_day']}")
        return

    print(f"\nPublishing {'(DRY RUN) ' if args.dry_run else ''}...")

    result = run_publish(
        client_slug=client_slug,
        pillar_day=content.day,
        week=folder["name"],
        dry_run=args.dry_run,
    )

    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    if not args.dry_run:
        save_state(client_slug, folder["name"], content.day)
        log_publish(client_slug, folder["name"], content.day, content.topic, result)

    print(f"\nDone. Results:")
    for platform, r in result.get("results", {}).items():
        status = "OK" if "error" not in r and "skipped" not in r else "FAIL"
        print(f"  {status} {platform}")

    print(f"\nState saved: {folder['name']} / Day {content.day}")


if __name__ == "__main__":
    main()

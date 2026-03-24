#!/usr/bin/env python3
"""
Golden Moments -> Social Engine Handoff Script
===============================================
Bridges the Golden Moments content generation pipeline to the Social Engine
pickup path. This script is the single point of handoff between the two systems.

WHAT IT DOES:
 1. Reads Golden Moments LinkedIn posts from:
 content/{client}-personal/linkedin/YYYY-wXX/
 2. Converts each post into the Social Engine's required format:
 - Frontmatter: type, day, topic, client, platforms, hashtags
 - Sections: ## Hook, ## Body, ## Engagement
 3. Saves converted files to a local staging directory (.state/)
 4. Creates a new Week-N subfolder in the client's Drive content pipeline folder
 5. Uploads all converted files to that Drive folder
 6. Updates the cloud state so cloud_daily_run.py knows content is ready

USAGE:
 python3 golden_moments_handoff.py --client your_client
 python3 golden_moments_handoff.py --client your_client --week 2026-W13
 python3 golden_moments_handoff.py --client your_client --dry-run

SCHEDULE:
 Run after Golden Moments content generation completes (Sunday evening).
 The cloud_daily_run.py hourly poll will pick up the state update automatically.

CONFIGURATION:
 Update DRIVE_CONTENT_FOLDERS, DEFAULT_PLATFORMS, and DEFAULT_HASHTAGS below
 to match your client setup before running.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_ROOT = os.path.join(SCRIPT_DIR, "content")
STATE_DIR = os.path.join(SCRIPT_DIR, ".state")

# ---------------------------------------------------------------------------
# Client configuration
# Update these values for your deployment.
# ---------------------------------------------------------------------------

# Google Drive folder IDs for each client's content pipeline folder
# Set to None to skip Drive upload (files will remain staged locally)
DRIVE_CONTENT_FOLDERS = {
 "your_client": None, # Replace with your Google Drive folder ID
 "client_b": None,
}

# Default platforms per client
DEFAULT_PLATFORMS = {
 "your_client": "linkedin, x, instagram, youtube_shorts, tiktok, facebook",
}

# Default hashtags per client (fallback if not extracted from post)
DEFAULT_HASHTAGS = {
 "your_client": "AI, AIAgents, BusinessAutomation, Entrepreneur",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_week_label() -> str:
 """Return current ISO week label, e.g. 2026-W13."""
 now = datetime.now(timezone.utc)
 return f"{now.year}-W{now.isocalendar()[1]:02d}"


def _find_linkedin_dir(client_slug: str, week_label: str) -> str | None:
 """
 Locate the Golden Moments LinkedIn output directory for a given week.
 Checks both YYYY-wXX (lowercase w) and YYYY-WXX (uppercase W) variants.
 """
 base = os.path.join(CONTENT_ROOT, f"{client_slug}-personal", "linkedin")
 if not os.path.isdir(base):
 return None
 for variant in [week_label.lower(), week_label.upper(), week_label]:
 candidate = os.path.join(base, variant)
 if os.path.isdir(candidate):
 return candidate
 return None


def _extract_topic(text: str, filename: str) -> str:
 """Extract topic from post frontmatter or derive from filename."""
 m = re.search(r"^topic:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
 if m:
 return m.group(1).strip()
 # Derive from filename: strip leading date/number prefix
 name = os.path.splitext(filename)[0]
 name = re.sub(r"^\d+[-_]", "", name)
 return name.replace("-", " ").replace("_", " ").title()


def _extract_hashtags(text: str, client_slug: str) -> str:
 """Extract hashtag line from post or fall back to client defaults."""
 m = re.search(r"^hashtags:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
 if m:
 return m.group(1).strip()
 # Look for a line of hashtags in the body
 for line in text.splitlines():
 words = line.strip().split()
 if words and sum(1 for w in words if w.startswith("#")) / len(words) > 0.6:
 tags = [w.lstrip("#") for w in words if w.startswith("#")]
 return ", ".join(tags)
 return DEFAULT_HASHTAGS.get(client_slug, "AI, Automation, Business")


def _split_hook_body_engagement(text: str) -> tuple[str, str, str]:
 """
 Split post text into Hook, Body, and Engagement sections.
 Falls back to heuristics if no explicit sections found.
 """
 # Try explicit section headers first
 hook_m = re.search(r"##\s*Hook\s*\n(.*?)(?=##|\Z)", text, re.DOTALL | re.IGNORECASE)
 body_m = re.search(r"##\s*Body\s*\n(.*?)(?=##|\Z)", text, re.DOTALL | re.IGNORECASE)
 eng_m = re.search(r"##\s*Engagement\s*\n(.*?)(?=##|\Z)", text, re.DOTALL | re.IGNORECASE)

 if hook_m and body_m:
 hook = hook_m.group(1).strip()
 body = body_m.group(1).strip()
 engagement = eng_m.group(1).strip() if eng_m else ""
 return hook, body, engagement

 # Heuristic split: first non-empty line = hook, rest = body
 lines = [l for l in text.splitlines() if l.strip()]
 # Strip frontmatter
 if lines and lines[0].startswith("---"):
 try:
 end = lines.index("---", 1)
 lines = lines[end + 1:]
 except ValueError:
 lines = lines[1:]

 if not lines:
 return "", text.strip(), ""

 hook = lines[0].strip()
 # Find engagement question (last line ending with ?)
 engagement = ""
 body_lines = lines[1:]
 if body_lines and body_lines[-1].strip().endswith("?"):
 engagement = body_lines[-1].strip()
 body_lines = body_lines[:-1]

 body = "\n".join(body_lines).strip()
 return hook, body, engagement


def _build_social_engine_post(raw_text: str, filename: str, day: int, client_slug: str) -> str:
 """Convert a Golden Moments post to Social Engine frontmatter + section format."""
 topic = _extract_topic(raw_text, filename)
 hashtags = _extract_hashtags(raw_text, client_slug)
 platforms = DEFAULT_PLATFORMS.get(client_slug, "linkedin, x")

 hook, body, engagement = _split_hook_body_engagement(raw_text)

 lines = [
 "---",
 f"type: linkedin",
 f"day: {day}",
 f"topic: {topic}",
 f"client: {client_slug}",
 f"platforms: {platforms}",
 f"hashtags: {hashtags}",
 "---",
 "",
 "## Hook",
 "",
 hook,
 "",
 "## Body",
 "",
 body,
 "",
 ]

 if engagement:
 lines += [
 "## Engagement",
 "",
 engagement,
 "",
 ]

 return "\n".join(lines)


# ---------------------------------------------------------------------------
# Drive helpers (requires gws CLI)
# ---------------------------------------------------------------------------

def _gws(args: list) -> tuple[int, str]:
 """Run a gws CLI command and return (returncode, stdout)."""
 result = subprocess.run(
 ["gws"] + args,
 capture_output=True, text=True
 )
 return result.returncode, result.stdout.strip()


def _next_week_number(parent_folder_id: str) -> int:
 """Find the highest existing Week-N folder and return N+1."""
 rc, out = _gws([
 "drive", "files", "list",
 "--params", json.dumps({"q": f'"{parent_folder_id}" in parents and mimeType = "application/vnd.google-apps.folder" and trashed = false'})
 ])
 if rc != 0:
 return 1
 try:
 data = json.loads(out)
 files = data.get("files", [])
 numbers = []
 for f in files:
 m = re.search(r"(\d+)", f.get("name", ""))
 if m:
 numbers.append(int(m.group(1)))
 return max(numbers) + 1 if numbers else 1
 except Exception:
 return 1


def _create_drive_folder(name: str, parent_id: str) -> str | None:
 """Create a subfolder in Drive and return its ID."""
 rc, out = _gws([
 "drive", "files", "create",
 "--json", json.dumps({
 "name": name,
 "mimeType": "application/vnd.google-apps.folder",
 "parents": [parent_id],
 })
 ])
 if rc != 0:
 return None
 try:
 return json.loads(out).get("id")
 except Exception:
 return None


def _upload_to_drive(filepath: str, parent_id: str) -> bool:
 """Upload a file to a Drive folder."""
 rc, _ = _gws(["drive", "+upload", filepath, "--parent", parent_id])
 return rc == 0


# ---------------------------------------------------------------------------
# State update
# ---------------------------------------------------------------------------

def _update_cloud_state(client_slug: str, week_label: str, converted_files: list, staging_dir: str):
 """Update the Social Engine cloud state to signal new content is ready."""
 state_file = os.path.join(STATE_DIR, f"{client_slug}_cloud_state.json")
 state = {}
 if os.path.exists(state_file):
 with open(state_file) as f:
 state = json.load(f)

 state["current_week"] = week_label
 state["weekly_scheduled"] = False
 state["weekly_scheduled_days"] = []
 state["pipeline_generated_at"] = datetime.now(timezone.utc).isoformat()
 state["handoff_source"] = "golden_moments"
 state["handoff_staging_dir"] = staging_dir
 state["handoff_file_count"] = len(converted_files)

 os.makedirs(STATE_DIR, exist_ok=True)
 with open(state_file, "w") as f:
 json.dump(state, f, indent=2)

 # Also reset the weekly approval state so the approval flow starts fresh
 approval_file = os.path.join(STATE_DIR, f"{client_slug}_weekly_approval.json")
 approval_state = {
 "week_label": week_label,
 "preview_sent_at": None,
 "preview_subject": None,
 "pending_days": list(range(1, len(converted_files) + 1)),
 "approved_days": [],
 "scheduled_days": [],
 "approval_received_at": None,
 }
 with open(approval_file, "w") as f:
 json.dump(approval_state, f, indent=2)

 print(f" Cloud state updated. Week: {week_label}, {len(converted_files)} posts ready.")


# ---------------------------------------------------------------------------
# Main handoff
# ---------------------------------------------------------------------------

def run_handoff(client_slug: str = "your_client", week_label: str = None, dry_run: bool = False):
 """
 Full handoff: read Golden Moments output, convert, upload to Drive,
 and update Social Engine state.
 """
 if week_label is None:
 week_label = _iso_week_label()

 print(f"\n{'='*60}")
 print(f" GOLDEN MOMENTS -> SOCIAL ENGINE HANDOFF")
 print(f" Client: {client_slug} | Week: {week_label}")
 print(f" Dry run: {dry_run}")
 print(f"{'='*60}\n")

 # Step 1: Locate Golden Moments LinkedIn posts
 print("STEP 1: Locating Golden Moments content...")
 linkedin_dir = _find_linkedin_dir(client_slug, week_label)
 if not linkedin_dir:
 print(f" [ERROR] No Golden Moments LinkedIn directory found for {client_slug} / {week_label}")
 print(f" Expected: {CONTENT_ROOT}/{client_slug}-personal/linkedin/{week_label.lower()}/")
 sys.exit(1)

 post_files = sorted([f for f in os.listdir(linkedin_dir) if f.endswith(".md")])
 if not post_files:
 print(f" [ERROR] No.md files found in {linkedin_dir}")
 sys.exit(1)

 print(f" Found {len(post_files)} post(s) in {linkedin_dir}")

 # Step 2: Convert each post to Social Engine format
 print("\nSTEP 2: Converting posts to Social Engine format...")
 staging_dir = os.path.join(STATE_DIR, f"{client_slug}_gm_handoff_{week_label}")
 os.makedirs(staging_dir, exist_ok=True)

 converted_files = []
 for day, filename in enumerate(post_files, start=1):
 src_path = os.path.join(linkedin_dir, filename)
 with open(src_path) as f:
 raw_text = f.read()

 converted = _build_social_engine_post(raw_text, filename, day, client_slug)
 topic_slug = re.sub(r"[^a-z0-9\-]", "", _extract_topic(raw_text, filename).lower().replace(" ", "-"))
 out_filename = f"post_day{day}_{topic_slug[:40]}.md"
 out_path = os.path.join(staging_dir, out_filename)

 if not dry_run:
 with open(out_path, "w") as f:
 f.write(converted)
 print(f" Day {day}: {filename} -> {out_filename}")
 converted_files.append(out_path)
 else:
 print(f" [DRY RUN] Day {day}: {filename} -> {out_filename}")
 print(f" Topic: {_extract_topic(raw_text, filename)}")

 if dry_run:
 print("\n[DRY RUN] No files written. No Drive upload. No state update.")
 return

 # Step 3: Create Drive Week-N folder and upload
 drive_folder_id = DRIVE_CONTENT_FOLDERS.get(client_slug)
 if not drive_folder_id:
 print(f"\nSTEP 3: [SKIP] No Drive folder configured for client '{client_slug}'.")
 print(f" Files staged locally at: {staging_dir}")
 else:
 print("\nSTEP 3: Uploading to Google Drive...")
 week_num = _next_week_number(drive_folder_id)
 week_name = f"Week-{week_num}"
 subfolder_id = _create_drive_folder(week_name, drive_folder_id)
 if not subfolder_id:
 print(f" [ERROR] Could not create Drive folder '{week_name}'. Files remain in: {staging_dir}")
 else:
 upload_ok = 0
 for filepath in converted_files:
 if _upload_to_drive(filepath, subfolder_id):
 upload_ok += 1
 print(f" Uploaded {upload_ok}/{len(converted_files)} files to Drive/{week_name}")

 # Step 4: Update Social Engine cloud state
 print("\nSTEP 4: Updating Social Engine cloud state...")
 _update_cloud_state(client_slug, week_label, converted_files, staging_dir)

 print(f"\n{'='*60}")
 print(f" HANDOFF COMPLETE")
 print(f" Posts converted: {len(converted_files)}")
 print(f" Staged at: {staging_dir}")
 print(f" Social Engine will pick up content on next hourly poll.")
 print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
 parser = argparse.ArgumentParser(
 description="Golden Moments -> Social Engine handoff script."
 )
 parser.add_argument("--client", default="your_client", help="Client slug (default: your_client)")
 parser.add_argument("--week", default=None, help="ISO week label, e.g. 2026-W13 (default: current week)")
 parser.add_argument("--dry-run", action="store_true", help="Preview conversion without writing or uploading")
 args = parser.parse_args()

 run_handoff(
 client_slug=args.client,
 week_label=args.week,
 dry_run=args.dry_run,
 )
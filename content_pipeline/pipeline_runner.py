"""
Pipeline Runner - orchestrates the full weekly content pipeline.

Runs every Sunday at 6:00 PM UTC (before the Monday 8 AM preview email).

FLOW:
  1. Run weekly_pipeline.py to generate 7 LinkedIn master post files
  2. Run post_builder.py on each file to derive all platform posts
  3. Upload all files to the client's Drive content pipeline folder
  4. Send Ryan a summary email of what was generated
  5. Update the .state file so cloud_daily_run.py picks up Day 1 on Monday

USAGE:
  python3 pipeline_runner.py --client ryan
  python3 pipeline_runner.py --client ryan --dry-run
  python3 pipeline_runner.py --client client_b
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_pipeline.weekly_pipeline import run_pipeline
from content_pipeline.post_builder import build_all_platforms

# ---------------------------------------------------------------------------
# Gmail MCP notification
# ---------------------------------------------------------------------------

def send_pipeline_summary_email(client_slug: str, week_label: str, generated_files: list, violations: list):
    """Send a summary email via Gmail MCP after pipeline generation."""
    import subprocess, json

    recipient = "your@email.com"  # Ryan's email
    if client_slug == "client_b":
        recipient = "client_b@your-brand.com"  # Placeholder for Client B

    subject = f"[{client_slug.upper()}] Weekly Content Pipeline Ready - {week_label}"

    file_list = "\n".join(f"  - {os.path.basename(f)}" for f in generated_files)
    violation_text = ""
    if violations:
        violation_text = "\n\nVIOLATIONS REQUIRING REVIEW:\n"
        for v in violations:
            violation_text += f"  Day {v['day']} ({v['pillar']}): {', '.join(v['violations'])}\n"

    body = f"""Weekly content pipeline has been generated for {week_label}.

{len(generated_files)} post files created and ready for review:

{file_list}
{violation_text}

The posts will be queued for daily preview emails starting Monday at 8:00 AM UTC.
Each post will require your APPROVE reply before it publishes.

READY, PLAN and GROW!
Trinity"""

    try:
        result = subprocess.run(
            ["manus-mcp-cli", "tool", "call", "gmail_send_messages", "--server", "gmail",
             "--input", json.dumps({
                 "messages": [{
                     "to": [recipient],
                     "subject": subject,
                     "content": body,
                 }]
             })],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"  Pipeline summary email sent to {recipient}")
        else:
            print(f"  Email send failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"  Email error: {e}")


# ---------------------------------------------------------------------------
# Drive upload
# ---------------------------------------------------------------------------

def upload_to_drive(files: list, client_slug: str, week_label: str):
    """Upload generated files to the client's Drive content pipeline folder."""
    # Drive folder IDs from client config
    drive_folder_map = {
        "your_client": "YOUR_DRIVE_FOLDER_ID",      # Ryan Content Pipeline
        "client_b": "PLACEHOLDER_MARCELA_DRIVE_FOLDER_ID",   # Client B Content Pipeline
    }

    folder_id = drive_folder_map.get(client_slug)
    if not folder_id or folder_id.startswith("PLACEHOLDER"):
        print(f"  Drive upload skipped: no folder ID configured for {client_slug}")
        return

    print(f"  Uploading {len(files)} files to Drive folder: {folder_id}")

    try:
        # Use gws CLI to upload files
        for filepath in files:
            result = subprocess.run(
                ["gws", "drive", "upload", filepath, "--folder", folder_id],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                print(f"    Uploaded: {os.path.basename(filepath)}")
            else:
                print(f"    Upload failed for {os.path.basename(filepath)}: {result.stderr[:100]}")
    except Exception as e:
        print(f"  Drive upload error: {e}")
        print("  Files remain in local .state directory")


# ---------------------------------------------------------------------------
# State updater
# ---------------------------------------------------------------------------

def update_pipeline_state(client_slug: str, week_label: str, generated_files: list, output_dir: str):
    """Update the .state file so cloud_daily_run.py knows about the new pipeline."""
    state_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".state")
    os.makedirs(state_dir, exist_ok=True)

    state_file = os.path.join(state_dir, f"{client_slug}_cloud_state.json")

    # Load existing state
    state = {}
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)

    # Update with new pipeline
    state["current_week"] = week_label
    state["pipeline_dir"] = output_dir
    state["pipeline_files"] = [os.path.basename(f) for f in generated_files]
    state["pipeline_generated_at"] = datetime.now(timezone.utc).isoformat()
    state["current_day"] = 1  # Reset to Day 1 for the new week

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    print(f"  State updated: {state_file}")
    print(f"  Week: {week_label} | Files: {len(generated_files)} | Starting Day 1")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(client_slug: str = "your_client", dry_run: bool = False):
    """Run the full pipeline: generate, build platforms, upload, notify."""
    now = datetime.now(timezone.utc)
    next_week = now + timedelta(days=7)
    week_label = f"{next_week.year}-W{next_week.isocalendar()[1]:02d}"

    print(f"\n{'='*60}")
    print(f"  WEEKLY CONTENT PIPELINE RUNNER")
    print(f"  Client: {client_slug} | Week: {week_label}")
    print(f"  Dry run: {dry_run}")
    print(f"{'='*60}\n")

    # Step 1: Generate 7 LinkedIn master posts
    print("STEP 1: Generating 7-day LinkedIn master posts...")
    pipeline_result = run_pipeline(
        client_slug=client_slug,
        dry_run=dry_run,
    )

    if dry_run:
        print("\n[DRY RUN] Pipeline generation previewed. No files written.")
        return

    generated_files = pipeline_result["files"]
    output_dir = pipeline_result["output_dir"]
    violations = pipeline_result["violations"]

    if not generated_files:
        print("No files generated. Aborting.")
        return

    # Step 2: Build platform-specific posts from each master post
    print(f"\nSTEP 2: Building platform posts from {len(generated_files)} master posts...")
    platform_dir = os.path.join(output_dir, "platforms")
    os.makedirs(platform_dir, exist_ok=True)

    all_platform_files = []
    for master_file in generated_files:
        results = build_all_platforms(master_file, output_dir=platform_dir)
        for platform, post in results.items():
            platform_file = os.path.join(
                platform_dir,
                f"{os.path.splitext(os.path.basename(master_file))[0]}_{platform}.md"
            )
            if os.path.exists(platform_file):
                all_platform_files.append(platform_file)

    print(f"  Platform posts built: {len(all_platform_files)}")

    # Step 3: Upload master posts to Drive
    print(f"\nSTEP 3: Uploading to Drive...")
    upload_to_drive(generated_files, client_slug, week_label)

    # Step 4: Update state
    print(f"\nSTEP 4: Updating pipeline state...")
    update_pipeline_state(client_slug, week_label, generated_files, output_dir)

    # Step 5: Send weekly approval preview email (7-day preview with APPROVE ALL reply)
    print(f"\nSTEP 5: Sending weekly approval preview email...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from weekly_approval import cmd_send_weekly_preview
        cmd_send_weekly_preview(client_slug, dry_run=False)
    except Exception as e:
        print(f"  Weekly approval email failed: {e}")
        # Fall back to simple summary email
        send_pipeline_summary_email(client_slug, week_label, generated_files, violations)

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Master posts: {len(generated_files)}")
    print(f"  Platform posts: {len(all_platform_files)}")
    print(f"  Violations: {len(violations)}")
    print(f"  Week {week_label} content is ready.")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly content pipeline runner")
    parser.add_argument("--client", default="your_client", help="Client slug (ryan or client_b)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing or uploading")
    args = parser.parse_args()

    run(client_slug=args.client, dry_run=args.dry_run)

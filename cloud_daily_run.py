"""
Cloud runner for the Social Engine.

Designed and built by Ryan Cunningham | https://www.readyplangrow.com
Ready, Plan, Grow! - AI-powered tools for founders and operators.

WEEKLY FLOW (automated):
 1. [Sunday 6 PM UTC] pipeline_runner.py generates 7 days of content
 2. [Sunday 6 PM UTC] weekly_approval.py sends 7-day preview email
 3. [Hourly, only while pending] weekly_approval.py polls Gmail for APPROVE ALL reply
 4. [On reply] Bulk-schedules all approved days into Blotato at 9 AM EST
 5. [On reply] Sends confirmation email listing all scheduled post times

MANUAL OVERRIDES:
 --force-post Post a specific day immediately (emergency use only)
 --status Show current pipeline state

NOTE: Daily preview emails have been removed. All approvals happen via the
weekly Sunday email. To edit or delete scheduled posts, use the Blotato dashboard.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

STATE_DIR = os.path.join(os.path.dirname(__file__), ".state")
os.makedirs(STATE_DIR, exist_ok=True)

CLIENT_EMAIL_CONFIG = {
 "your_client": {
 "send_to": "your@email.com",
 "reply_from": "your@email.com",
 "subject_prefix": "[Your Client Social Engine]",
 "display_name": "Your Client",
 },
 "client_b": {
 "send_to": "client_b@example.com",
 "reply_from": "client_b@example.com",
 "subject_prefix": "[Client B Social Engine]",
 "display_name": "Client B",
 },
}


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _state_file(slug: str) -> str:
 return os.path.join(STATE_DIR, f"{slug}_cloud_state.json")


def _load_state(slug: str) -> dict:
 path = _state_file(slug)
 if os.path.exists(path):
 with open(path) as f:
 return json.load(f)
 return {
 "current_week": None,
 "weekly_scheduled": False,
 "weekly_scheduled_days": [],
 "pipeline_generated_at": None,
 }


def _save_state(slug: str, state: dict):
 with open(_state_file(slug), "w") as f:
 json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Gmail helper (for force-post confirmation only)
# ---------------------------------------------------------------------------

def _send_email(to: str, subject: str, body: str):
 cmd = [
 "manus-mcp-cli", "tool", "call", "gmail_send_messages",
 "--server", "gmail",
 "--input", json.dumps({"messages": [{"to": [to], "subject": subject, "content": body}]}),
 ]
 subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(slug: str):
 """Print current pipeline state."""
 state = _load_state(slug)

 # Also show weekly approval state if available
 weekly_state_file = os.path.join(STATE_DIR, f"{slug}_weekly_approval.json")
 weekly_state = {}
 if os.path.exists(weekly_state_file):
 with open(weekly_state_file) as f:
 weekly_state = json.load(f)

 print(f"\n[{slug}] Social Engine Status")
 print(f" Current week: {state.get('current_week', 'None')}")
 print(f" Pipeline generated: {state.get('pipeline_generated_at', 'Never')}")
 print(f" Weekly scheduled: {state.get('weekly_scheduled', False)}")
 print(f" Scheduled days: {state.get('weekly_scheduled_days', [])}")
 print()
 if weekly_state:
 print(f" Weekly approval:")
 print(f" Preview sent: {weekly_state.get('preview_sent_at', 'Never')}")
 print(f" Approval received: {weekly_state.get('approval_received_at', 'Not yet')}")
 print(f" Approved days: {weekly_state.get('approved_days', [])}")
 print()


def cmd_force_post(slug: str, day: int = None):
 """
 Emergency override: post a specific day immediately without approval.
 Bypasses the weekly schedule and posts right now.
 """
 from engine.workflow import run_publish

 state = _load_state(slug)
 email_cfg = CLIENT_EMAIL_CONFIG.get(slug, {})

 # Default to Day 1 if no day specified
 if not day:
 day = 1
 print(f"[{slug}] No day specified. Defaulting to Day 1.")

 print(f"[{slug}] FORCE POST: Publishing Day {day} immediately...")
 result = run_publish(client_slug=slug, pillar_day=day, dry_run=False)

 if "error" in result:
 print(f"[{slug}] Force post failed: {result['error']}")
 return

 print(f"[{slug}] Day {day} force-posted successfully.")

 if email_cfg.get("send_to"):
 lines = [f"Social Engine - {email_cfg['display_name']} - Day {day} Force-Published", ""]
 results = result.get("results", {})
 for platform, res in results.items():
 status = "FAILED" if "error" in res else "Posted"
 lines.append(f" {platform:<20} {status}")
 _send_email(
 to=email_cfg["send_to"],
 subject=f"{email_cfg['subject_prefix']} Day {day} Force-Published",
 body="\n".join(lines),
 )


def cmd_run(slug: str):
 """
 Unified hourly run mode used by the scheduled task.
 - Sunday 18:00-18:59 UTC: run the weekly pipeline + send approval email
 - All other times: poll Gmail for APPROVE ALL reply ONLY IF a preview is
 pending and the week has not already been scheduled.

 RESOURCE POLICY: Do NOT poll Gmail unless there is an outstanding preview
 email awaiting a reply. Once approved and scheduled, polling stops until
 the next preview email is sent (next Sunday).
 """
 now = datetime.now(timezone.utc)
 is_sunday = now.weekday() == 6 # Sunday
 is_pipeline_hour = now.hour == 18

 if is_sunday and is_pipeline_hour:
 print(f"[{slug}] Sunday 6 PM: running weekly content pipeline...")
 result = subprocess.run(
 [sys.executable, "content_pipeline/pipeline_runner.py", "--client", slug],
 cwd=os.path.dirname(__file__),
 capture_output=False,
 )
 if result.returncode != 0:
 print(f"[{slug}] Pipeline failed with exit code {result.returncode}")
 else:
 # Guard: only poll if a preview email is pending AND week is not yet scheduled
 weekly_state_file = os.path.join(STATE_DIR, f"{slug}_weekly_approval.json")
 weekly_state = {}
 if os.path.exists(weekly_state_file):
 with open(weekly_state_file) as f:
 import json as _json
 weekly_state = _json.load(f)

 preview_sent = weekly_state.get("preview_sent_at")
 already_scheduled = bool(weekly_state.get("scheduled_days"))

 if not preview_sent:
 print(f"[{slug}] No preview email pending. Skipping poll.")
 return
 if already_scheduled:
 print(f"[{slug}] Week already approved and scheduled. Skipping poll.")
 return

 # Only reaches here if preview was sent and approval has not been received yet
 print(f"[{slug}] Preview pending since {preview_sent}. Polling for approval reply...")
 result = subprocess.run(
 [sys.executable, "weekly_approval.py", "--client", slug, "--poll"],
 cwd=os.path.dirname(__file__),
 capture_output=False,
 )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
 sys.path.insert(0, os.path.dirname(__file__))

 parser = argparse.ArgumentParser(description="Social Engine cloud runner")
 parser.add_argument("--client", required=True, help="Client slug (e.g. your_client or client_b)")
 parser.add_argument("--run", action="store_true",
 help="Unified mode: run pipeline Sunday 6 PM, poll all other times (use for scheduled task)")
 parser.add_argument("--status", action="store_true", help="Show current pipeline state")
 parser.add_argument("--force-post", action="store_true", help="Post a specific day immediately")
 parser.add_argument("--day", type=int, help="Day number for --force-post (default: 1)")
 args = parser.parse_args()

 if args.run:
 cmd_run(args.client)
 elif args.status:
 cmd_status(args.client)
 elif args.force_post:
 cmd_force_post(args.client, day=args.day)
 else:
 print("Specify --run, --status, or --force-post")
 parser.print_help()
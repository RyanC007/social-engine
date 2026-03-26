"""
Hybrid Weekly Approval System for the Social Engine.

Designed and built by Ryan Cunningham | https://www.readyplangrow.com
Ready, Plan, Grow! - AI-powered tools for founders and operators.

FLOW:
 1. Sunday 6 PM - pipeline_runner.py generates 7 days of content
 2. Sunday 6:05 PM - weekly_approval.py sends a full 7-day preview email
 3. The client reviews on their phone or computer and replies with one of:
 APPROVE ALL -> Schedule all 7 days into Blotato
 APPROVE ALL SKIP 3 5 -> Schedule all days except Day 3 and Day 5
 SKIP ALL -> Discard this week (rare)
 4. Engine polls Gmail for the reply, parses it, and bulk-schedules approved days
 5. Client receives a confirmation email listing all scheduled post times

SCHEDULE LOGIC:
 Posts are scheduled to publish at 9:00 AM EST (14:00 UTC) on each day.
 Day 1 = Monday, Day 2 = Tuesday,..., Day 7 = Sunday.
 The engine calculates the correct date for each day based on the upcoming Monday.

COMMANDS (reply with one of these):
 APPROVE ALL Schedule all 7 days
 APPROVE ALL SKIP 3 Schedule all days except Day 3
 APPROVE ALL SKIP 3 5 7 Schedule all days except Days 3, 5, and 7
 SKIP ALL Discard this week entirely
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

STATE_DIR = os.path.join(os.path.dirname(__file__), ".state")
os.makedirs(STATE_DIR, exist_ok=True)

# Post time: 9:00 AM EST = 14:00 UTC
POST_HOUR_UTC = 14
POST_MINUTE_UTC = 0

# Day-of-week mapping: Day 1 = Monday (weekday 0), Day 7 = Sunday (weekday 6)
DAY_WEEKDAY_MAP = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}

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
 return os.path.join(STATE_DIR, f"{slug}_weekly_approval.json")


def _load_state(slug: str) -> dict:
 path = _state_file(slug)
 if os.path.exists(path):
 with open(path) as f:
 return json.load(f)
 return {
 "week_label": None,
 "preview_sent_at": None,
 "preview_subject": None,
 "pending_days": [],
 "approved_days": [],
 "scheduled_days": [],
 "approval_received_at": None,
 }


def _save_state(slug: str, state: dict):
 with open(_state_file(slug), "w") as f:
 json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------

def _mcp(tool: str, args: dict) -> dict:
 cmd = [
 "manus-mcp-cli", "tool", "call", tool,
 "--server", "gmail",
 "--input", json.dumps(args),
 ]
 result = subprocess.run(cmd, capture_output=True, text=True)
 if result.returncode != 0:
 return {"error": result.stderr.strip()}
 try:
 output = result.stdout.strip()
 # Try to find and parse the first JSON object in the output
 start = output.find("{")
 if start >= 0:
 parsed = json.loads(output[start:])
 # If the result is wrapped in a 'result' key, unwrap it
 if "result" in parsed:
 inner = parsed["result"]
 if isinstance(inner, list):
 return {"threads": inner}
 if isinstance(inner, dict):
 return inner
 return parsed
 return {"raw": output}
 except Exception as e:
 return {"error": str(e), "raw": result.stdout.strip()}


def _send_email(to: str, subject: str, body: str) -> dict:
 return _mcp("gmail_send_messages", {
 "messages": [{
 "to": [to],
 "subject": subject,
 "content": body,
 }]
 })


def _search_emails(query: str, max_results: int = 5) -> list:
 result = _mcp("gmail_search_messages", {"q": query, "max_results": max_results})
 return result.get("messages", [])


def _read_thread(thread_id: str) -> dict:
 result = _mcp("gmail_read_threads", {
 "thread_ids": [thread_id],
 "include_full_messages": True,
 })
 threads = result.get("threads", [])
 return threads[0] if threads else {}


# ---------------------------------------------------------------------------
# Schedule time calculator
# ---------------------------------------------------------------------------

def _get_post_schedule_times(week_start_monday: datetime) -> dict:
 """
 Return a dict of {day_number: ISO8601 schedule string} for the coming week.
 Posts at POST_HOUR_UTC:POST_MINUTE_UTC UTC each day.
 Day 1 = Monday, Day 7 = Sunday.
 """
 times = {}
 for day_num, weekday_offset in DAY_WEEKDAY_MAP.items():
 post_date = week_start_monday + timedelta(days=weekday_offset)
 post_dt = post_date.replace(
 hour=POST_HOUR_UTC,
 minute=POST_MINUTE_UTC,
 second=0,
 microsecond=0,
 tzinfo=timezone.utc,
 )
 times[day_num] = post_dt.isoformat()
 return times


def _next_monday() -> datetime:
 """Return the datetime of the upcoming Monday (or today if today is Monday)."""
 now = datetime.now(timezone.utc)
 days_until_monday = (7 - now.weekday()) % 7
 if days_until_monday == 0:
 days_until_monday = 7 # Always go to NEXT Monday from Sunday pipeline run
 return now + timedelta(days=days_until_monday)


# ---------------------------------------------------------------------------
# Preview email builder
# ---------------------------------------------------------------------------

def _build_weekly_preview_email(
 slug: str,
 week_label: str,
 day_previews: list,
 email_cfg: dict,
 schedule_times: dict,
) -> str:
 """Build the full 7-day preview email body."""
 name = email_cfg["display_name"]

 lines = [
 f"Weekly Content Preview - {name} - {week_label}",
 f"Generated: {datetime.now(timezone.utc).strftime('%A %B %d, %Y at %H:%M UTC')}",
 "",
 "=" * 70,
 "REPLY WITH ONE OF THESE COMMANDS:",
 "",
 " APPROVE ALL -> Schedule all 7 days",
 " APPROVE ALL SKIP 3 -> Schedule all except Day 3",
 " APPROVE ALL SKIP 3 5 7 -> Schedule all except Days 3, 5, and 7",
 " SKIP ALL -> Discard this week",
 "",
 "Posts will be scheduled at 9:00 AM EST each day.",
 "=" * 70,
 "",
 ]

 for preview in day_previews:
 day_num = preview["day"]
 topic = preview.get("topic", "Unknown")
 pillar = preview.get("pillar_type", "post")
 schedule_time = schedule_times.get(day_num, "")
 # Format schedule time for display
 try:
 dt = datetime.fromisoformat(schedule_time)
 # Convert UTC to EST (UTC-5)
 est_hour = (dt.hour - 5) % 24
 schedule_display = dt.strftime(f"%A %B %d - {est_hour:02d}:{dt.minute:02d} AM EST")
 except Exception:
 schedule_display = schedule_time

 lines += [
 f"{'=' * 70}",
 f"DAY {day_num} - {schedule_display}",
 f"Topic: {topic} | Type: {pillar}",
 f"{'=' * 70}",
 "",
 ]

 platforms = preview.get("platforms", {})
 for platform, text in platforms.items():
 lines.append(f"--- {platform.upper()} ---")
 lines.append(text[:500] + ("..." if len(text) > 500 else ""))
 lines.append("")

 # Flag any violations
 violations = preview.get("violations", [])
 if violations:
 lines.append(f" VIOLATIONS: {', '.join(violations)}")
 lines.append("")

 lines += [
 "=" * 70,
 "Nothing has been posted. Your reply schedules the content.",
 f"Scheduled posts can be edited or deleted in your Blotato dashboard.",
 "=" * 70,
 ]

 return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reply parser
# ---------------------------------------------------------------------------

def _parse_approval_reply(body: str) -> dict:
 """
 Parse the reply body and return:
 {
 "command": "APPROVE_ALL" | "SKIP_ALL" | None,
 "skip_days": [3, 5], # days to skip if APPROVE ALL SKIP...
 }
 """
 body_upper = body.upper().strip()[:500] # Only check first 500 chars

 if "SKIP ALL" in body_upper:
 return {"command": "SKIP_ALL", "skip_days": []}

 if "APPROVE ALL" in body_upper:
 # Look for SKIP followed by day numbers
 skip_match = re.search(r"APPROVE ALL\s+SKIP\s+([\d\s]+)", body_upper)
 skip_days = []
 if skip_match:
 skip_days = [int(d) for d in skip_match.group(1).split() if d.isdigit() and 1 <= int(d) <= 7]
 return {"command": "APPROVE_ALL", "skip_days": skip_days}

 return {"command": None, "skip_days": []}


# ---------------------------------------------------------------------------
# Bulk scheduler
# ---------------------------------------------------------------------------

def _bulk_schedule(slug: str, approved_days: list, schedule_times: dict, email_cfg: dict):
 """
 Schedule all approved days into Blotato at their calculated times.
 Returns a dict of {day: result}.
 """
 from engine.workflow import run_publish

 results = {}
 print(f"\n[{slug}] Bulk scheduling {len(approved_days)} days into Blotato...")

 for day_num in sorted(approved_days):
 schedule_at = schedule_times.get(day_num)
 print(f" Scheduling Day {day_num} for {schedule_at}...")

 result = run_publish(
 client_slug=slug,
 pillar_day=day_num,
 schedule_at=schedule_at,
 dry_run=False,
 )

 if "error" in result:
 print(f" Day {day_num} FAILED: {result['error']}")
 results[day_num] = {"status": "failed", "error": result["error"]}
 else:
 print(f" Day {day_num} scheduled successfully.")
 results[day_num] = {"status": "scheduled", "schedule_at": schedule_at}

 return results


# ---------------------------------------------------------------------------
# Confirmation email builder
# ---------------------------------------------------------------------------

def _build_schedule_confirmation_email(
 slug: str,
 week_label: str,
 approved_days: list,
 skipped_days: list,
 schedule_results: dict,
 schedule_times: dict,
 email_cfg: dict,
) -> str:
 name = email_cfg["display_name"]

 lines = [
 f"Weekly Schedule Confirmed - {name} - {week_label}",
 "",
 f"The following posts have been scheduled into Blotato:",
 "",
 ]

 for day_num in sorted(approved_days):
 result = schedule_results.get(day_num, {})
 status = result.get("status", "unknown")
 schedule_at = schedule_times.get(day_num, "")
 try:
 dt = datetime.fromisoformat(schedule_at)
 est_hour = (dt.hour - 5) % 24
 time_display = dt.strftime(f"%A %B %d at {est_hour:02d}:{dt.minute:02d} AM EST")
 except Exception:
 time_display = schedule_at

 status_icon = "SCHEDULED" if status == "scheduled" else "FAILED"
 lines.append(f" Day {day_num} - {time_display} - {status_icon}")
 if status == "failed":
 lines.append(f" Error: {result.get('error', 'Unknown error')}")

 if skipped_days:
 lines += [
 "",
 f"Skipped days (not scheduled): {', '.join(f'Day {d}' for d in sorted(skipped_days))}",
 ]

 failed = [d for d, r in schedule_results.items() if r.get("status") == "failed"]
 if failed:
 lines += [
 "",
 f"WARNING: {len(failed)} day(s) failed to schedule. Check the engine logs.",
 ]

 lines += [
 "",
 "You can view, edit, or delete scheduled posts in your Blotato dashboard.",
 "",
 "READY, PLAN and GROW!",
 "Trinity",
 ]

 return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core commands
# ---------------------------------------------------------------------------

def cmd_send_weekly_preview(slug: str, dry_run: bool = False):
 """
 Build a dry-run preview of all 7 days and send the weekly approval email.
 Called by pipeline_runner.py after content generation.
 """
 from engine.workflow import run_publish

 email_cfg = CLIENT_EMAIL_CONFIG.get(slug)
 if not email_cfg:
 print(f"[{slug}] No email config found.")
 return

 state = _load_state(slug)
 cloud_state_file = os.path.join(STATE_DIR, f"{slug}_cloud_state.json")

 # Get week label from the cloud state
 week_label = "Unknown Week"
 if os.path.exists(cloud_state_file):
 with open(cloud_state_file) as f:
 cloud_state = json.load(f)
 week_label = cloud_state.get("current_week", week_label)

 print(f"[{slug}] Building 7-day preview for {week_label}...")

 # Calculate schedule times for the coming week
 next_monday = _next_monday()
 schedule_times = _get_post_schedule_times(next_monday)

 # Build dry-run previews for all 7 days
 day_previews = []
 for day_num in range(1, 8):
 print(f" Previewing Day {day_num}...")
 result = run_publish(client_slug=slug, pillar_day=day_num, dry_run=True)

 if "error" in result:
 print(f" Day {day_num} preview error: {result['error']}")
 day_previews.append({
 "day": day_num,
 "topic": f"ERROR: {result['error']}",
 "pillar_type": "error",
 "platforms": {},
 "violations": [result["error"]],
 })
 else:
 pillar_info = result.get("pillar", {})
 platforms = result.get("platforms", {})
 day_previews.append({
 "day": day_num,
 "topic": pillar_info.get("topic", "Unknown"),
 "pillar_type": pillar_info.get("type", "post"),
 "platforms": platforms,
 "violations": [],
 })

 if dry_run:
 print(f"\n[DRY RUN] Would send weekly preview email to {email_cfg['send_to']}")
 for p in day_previews:
 print(f" Day {p['day']}: {p['topic']}")
 return

 # Build and send the preview email
 subject = f"{email_cfg['subject_prefix']} Weekly Preview {week_label} - Reply APPROVE ALL to schedule"
 body = _build_weekly_preview_email(slug, week_label, day_previews, email_cfg, schedule_times)

 print(f"[{slug}] Sending weekly preview email to {email_cfg['send_to']}...")
 _send_email(to=email_cfg["send_to"], subject=subject, body=body)

 # Save state
 state["week_label"] = week_label
 state["preview_sent_at"] = datetime.now(timezone.utc).isoformat()
 state["preview_subject"] = subject
 state["pending_days"] = list(range(1, 8))
 state["approved_days"] = []
 state["scheduled_days"] = []
 state["schedule_times"] = schedule_times
 _save_state(slug, state)

 print(f"[{slug}] Weekly preview sent. Waiting for APPROVE ALL reply.")


def cmd_poll_weekly(slug: str):
 """
 Poll Gmail for the APPROVE ALL reply and bulk-schedule if found.
 Run ONCE on-demand when instructed. Do NOT schedule or loop.
 """
 email_cfg = CLIENT_EMAIL_CONFIG.get(slug)
 if not email_cfg:
 print(f"[{slug}] No email config found.")
 return

 state = _load_state(slug)

 if not state.get("preview_sent_at"):
 print(f"[{slug}] No weekly preview pending. Nothing to poll for.")
 return

 if state.get("scheduled_days"):
 print(f"[{slug}] Week already scheduled. Days: {state['scheduled_days']}")
 return

 week_label = state.get("week_label", "Unknown")
 print(f"[{slug}] Polling Gmail for weekly approval reply ({week_label})...")

 # Search for replies to the weekly preview email
 today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
 query = f"from:{email_cfg['reply_from']} subject:\"Weekly Preview\" after:{today}"
 messages = _search_emails(query, max_results=5)

 if not messages:
 # Also try searching the last 3 days in case of delay
 three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
 query = f"from:{email_cfg['reply_from']} subject:\"Weekly Preview\" after:{three_days_ago}"
 messages = _search_emails(query, max_results=5)

 if not messages:
 print(f"[{slug}] No reply found yet.")
 return

 # Read the most recent matching thread
 for msg in messages:
 thread_id = msg.get("threadId")
 if not thread_id:
 continue

 thread = _read_thread(thread_id)
 thread_messages = thread.get("messages", [])

 for thread_msg in reversed(thread_messages):
 body = ""
 payload = thread_msg.get("payload", {})
 parts = payload.get("parts", [])
 if parts:
 for part in parts:
 if part.get("mimeType") == "text/plain":
 data = part.get("body", {}).get("data", "")
 if data:
 import base64
 body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
 break
 else:
 data = payload.get("body", {}).get("data", "")
 if data:
 import base64
 body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

 parsed = _parse_approval_reply(body)

 if parsed["command"] == "SKIP_ALL":
 print(f"[{slug}] SKIP ALL received. Discarding week {week_label}.")
 state["scheduled_days"] = []
 state["approved_days"] = []
 _save_state(slug, state)
 _send_email(
 to=email_cfg["send_to"],
 subject=f"{email_cfg['subject_prefix']} Week {week_label} Skipped",
 body=f"Week {week_label} has been skipped. No posts were scheduled.\n\nThe next week's content will be generated on Sunday.",
 )
 return

 if parsed["command"] == "APPROVE_ALL":
 skip_days = parsed["skip_days"]
 approved_days = [d for d in range(1, 8) if d not in skip_days]
 schedule_times = state.get("schedule_times", {})

 # Convert string keys back to int (JSON serializes dict keys as strings)
 schedule_times = {int(k): v for k, v in schedule_times.items()}

 print(f"[{slug}] APPROVE ALL received. Skipping: {skip_days}. Scheduling: {approved_days}")

 # Bulk schedule all approved days
 schedule_results = _bulk_schedule(slug, approved_days, schedule_times, email_cfg)

 # Update state
 state["approved_days"] = approved_days
 state["scheduled_days"] = [d for d, r in schedule_results.items() if r.get("status") == "scheduled"]
 state["approval_received_at"] = datetime.now(timezone.utc).isoformat()
 _save_state(slug, state)

 # Update cloud_daily_run state to reflect the week is handled
 cloud_state_file = os.path.join(STATE_DIR, f"{slug}_cloud_state.json")
 if os.path.exists(cloud_state_file):
 with open(cloud_state_file) as f:
 cloud_state = json.load(f)
 cloud_state["weekly_scheduled"] = True
 cloud_state["weekly_scheduled_days"] = state["scheduled_days"]
 with open(cloud_state_file, "w") as f:
 json.dump(cloud_state, f, indent=2)

 # Send confirmation email
 _send_email(
 to=email_cfg["send_to"],
 subject=f"{email_cfg['subject_prefix']} Week {week_label} Scheduled - {len(state['scheduled_days'])} posts queued",
 body=_build_schedule_confirmation_email(
 slug, week_label, approved_days, skip_days,
 schedule_results, schedule_times, email_cfg
 ),
 )
 print(f"[{slug}] Week {week_label} scheduled. {len(state['scheduled_days'])} posts queued in Blotato.")
 return

 print(f"[{slug}] No actionable reply found yet.")


def cmd_status(slug: str):
 """Print current weekly approval state."""
 state = _load_state(slug)
 print(f"\n[{slug}] Weekly Approval State:")
 print(f" Week: {state.get('week_label', 'None')}")
 print(f" Preview sent: {state.get('preview_sent_at', 'Never')}")
 print(f" Pending days: {state.get('pending_days', [])}")
 print(f" Approved days: {state.get('approved_days', [])}")
 print(f" Scheduled days: {state.get('scheduled_days', [])}")
 print(f" Approval received: {state.get('approval_received_at', 'Not yet')}")
 print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
 parser = argparse.ArgumentParser(description="Weekly approval system for the Social Engine")
 parser.add_argument("--client", required=True, help="Client slug: ryan or client_b")
 parser.add_argument("--send-preview", action="store_true", help="Build 7-day preview and send approval email")
 parser.add_argument("--poll", action="store_true", help="Poll Gmail for APPROVE ALL reply")
 parser.add_argument("--status", action="store_true", help="Show current weekly approval state")
 parser.add_argument("--dry-run", action="store_true", help="Preview without sending email")
 args = parser.parse_args()

 if args.send_preview:
 cmd_send_weekly_preview(args.client, dry_run=args.dry_run)
 elif args.poll:
 cmd_poll_weekly(args.client)
 elif args.status:
 cmd_status(args.client)
 else:
 print("Specify --send-preview, --poll, or --status")
 parser.print_help()
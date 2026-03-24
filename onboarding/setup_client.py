#!/usr/bin/env python3
"""
New client onboarding wizard.

Walks through setting up a new client config file in clients/{slug}.json.
Run: python onboarding/setup_client.py

What it collects:
  1. Client name + slug
  2. Blotato API key (verified against the API)
  3. Blotato account IDs for each platform (listed live from their API)
  4. Google Drive folder IDs (content + knowledge base)
  5. Service account JSON path
  6. Brand description

Output: clients/{slug}.json (ready to use)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

CLIENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "clients")
BLOTATO_BASE_URL = "https://backend.blotato.com/v2"

console = Console()

PLATFORM_NAMES = {
    "linkedin": "LinkedIn",
    "x": "X / Twitter",
    "instagram": "Instagram",
    "youtube": "YouTube",
    "facebook": "Facebook",
}


def blotato_get(api_key: str, endpoint: str) -> dict:
    resp = requests.get(
        f"{BLOTATO_BASE_URL}{endpoint}",
        headers={"blotato-api-key": api_key, "Content-Type": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def list_blotato_accounts(api_key: str) -> list:
    data = blotato_get(api_key, "/accounts")
    return data.get("items", [])


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def main():
    console.rule("[bold blue]Social Engine  - New Client Setup")
    console.print(
        "\nThis wizard creates a client config file so the engine can publish "
        "for a new client.\n"
    )

    # ── 1. Name + slug ─────────────────────────────────────────────────────
    name = Prompt.ask("[bold]Client full name[/bold]")
    default_slug = slugify(name)
    slug = Prompt.ask(f"[bold]Slug[/bold] (used in file names / commands)", default=default_slug)
    slug = slugify(slug)

    output_path = os.path.join(CLIENTS_DIR, f"{slug}.json")
    if os.path.exists(output_path):
        overwrite = Confirm.ask(
            f"[yellow]clients/{slug}.json already exists. Overwrite?[/yellow]",
            default=False,
        )
        if not overwrite:
            console.print("[red]Aborted.[/red]")
            return

    # ── 2. Blotato API key ──────────────────────────────────────────────────
    console.print("\n[bold]Blotato API key[/bold]")
    console.print("  Find it at: https://app.blotato.com → Settings → API")
    api_key = Prompt.ask("API key").strip()

    console.print("  Verifying API key...", end="")
    try:
        accounts = list_blotato_accounts(api_key)
        console.print(f" [green]✓ {len(accounts)} account(s) found[/green]")
    except Exception as e:
        console.print(f"\n[red]Failed to connect: {e}[/red]")
        return

    # ── 3. Match platforms to accounts ─────────────────────────────────────
    console.print("\n[bold]Platform accounts[/bold]")
    console.print("Match each platform to the Blotato account ID.\n")

    # Show all accounts in a table
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Account ID", width=10)
    table.add_column("Platform")
    table.add_column("Username / Name")
    for i, acct in enumerate(accounts):
        table.add_row(
            str(i + 1),
            acct.get("id", ""),
            acct.get("platform", ""),
            acct.get("username") or acct.get("name", ""),
        )
    console.print(table)

    client_accounts = {}
    for platform_key, platform_label in PLATFORM_NAMES.items():
        use = Confirm.ask(f"Does this client post to [bold]{platform_label}[/bold]?", default=True)
        if not use:
            continue
        acct_id = Prompt.ask(f"  Account ID for {platform_label}").strip()
        entry = {"account_id": acct_id}

        # Facebook: also need page_id
        if platform_key == "facebook":
            page_id = Prompt.ask("  Facebook page ID (leave blank if none)", default="").strip()
            if page_id:
                entry["page_id"] = page_id

        client_accounts[platform_key] = entry

    # ── 4. LinkedIn company pages (optional) ──────────────────────────────
    linkedin_pages = {}
    if "linkedin" in client_accounts:
        add_pages = Confirm.ask("\nAdd LinkedIn company pages?", default=False)
        while add_pages:
            lbl = Prompt.ask("  Company page key (e.g. 'acme_corp')").strip()
            page_id = Prompt.ask("  LinkedIn page ID (numeric)").strip()
            linkedin_pages[lbl] = page_id
            add_pages = Confirm.ask("  Add another LinkedIn page?", default=False)

    # ── 5. Facebook pages (optional) ──────────────────────────────────────
    facebook_pages = {}
    if "facebook" in client_accounts:
        add_fb = Confirm.ask("\nAdd additional Facebook pages?", default=False)
        while add_fb:
            lbl = Prompt.ask("  Page key (e.g. 'main_page')").strip()
            page_id = Prompt.ask("  Facebook page ID").strip()
            facebook_pages[lbl] = page_id
            add_fb = Confirm.ask("  Add another Facebook page?", default=False)

    # ── 6. Google Drive ───────────────────────────────────────────────────
    console.print("\n[bold]Google Drive[/bold]")
    console.print(
        "Share the client's content folder and knowledge base folder with the "
        "service account:\n"
        "  your-service-account@your-project.iam.gserviceaccount.com\n"
    )
    content_folder_id = Prompt.ask("  Content folder ID (from Drive URL)").strip()
    kb_folder_id = Prompt.ask("  Knowledge base folder ID (from Drive URL)").strip()

    sa_file = Prompt.ask(
        "  Service account JSON path",
        default="service_account.json",
    ).strip()

    # ── 7. Brand ──────────────────────────────────────────────────────────
    console.print("\n[bold]Brand description[/bold]")
    niche = Prompt.ask("  Niche / topic area (e.g. 'AI tools for real estate agents')").strip()
    voice = Prompt.ask("  Brand voice (e.g. 'practical, no-fluff, results-driven')").strip()

    # ── 8. Write config ───────────────────────────────────────────────────
    config = {
        "name": name,
        "slug": slug,
        "blotato_api_key_env": f"BLOTATO_API_KEY_{slug.upper()}",
        "drive": {
            "content_folder_id": content_folder_id,
            "knowledge_base_folder_id": kb_folder_id,
            "service_account_file": sa_file,
        },
        "accounts": client_accounts,
        "linkedin_pages": linkedin_pages,
        "facebook_pages": facebook_pages,
        "brand": {
            "niche": niche,
            "voice": voice,
        },
        "visual_templates": {
            "youtube_shorts": "/base/v2/ai-story-video/5903fe43-514d-40ee-a060-0d6628c5f8fd/v1",
            "instagram_quote": "9f4e66cd-b784-4c02-b2ce-e6d0765fd4c0",
        },
    }

    os.makedirs(CLIENTS_DIR, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        Panel(
            f"[green]✓ Client '{name}' configured![/green]\n\n"
            f"Config saved to: [bold]clients/{slug}.json[/bold]\n\n"
            f"Next steps:\n"
            f"  1. Add the Blotato API key to your .env:\n"
            f"     [bold]BLOTATO_API_KEY_{slug.upper()}=blt_...[/bold]\n\n"
            f"  2. Share the Drive folders with the service account.\n\n"
            f"  3. Test with:\n"
            f"     [bold]python main.py --client {slug} --dry-run[/bold]",
            title="Setup complete",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()

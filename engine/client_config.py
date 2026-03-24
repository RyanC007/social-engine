"""
Client configuration loader.

Each client is a JSON file in the clients/ directory.
The engine uses ClientConfig everywhere instead of the global config.py,
so the same code can serve Ryan, future clients, and the MCP server.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional

CLIENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "clients")
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


@dataclass
class ClientConfig:
    name: str
    slug: str
    blotato_api_key: str
    drive_content_folder_id: str
    drive_knowledge_base_folder_id: str
    drive_service_account_file: str      # absolute path to service account JSON (fallback)
    drive_token_file: str = ""             # absolute path to OAuth token JSON (preferred)

    accounts: dict = field(default_factory=dict)
    linkedin_pages: dict = field(default_factory=dict)
    facebook_pages: dict = field(default_factory=dict)
    brand: dict = field(default_factory=dict)
    visual_templates: dict = field(default_factory=dict)
    _default_facebook_page: str = ""

    def tiktok_handle(self) -> str:
        return self.brand.get("tiktok_handle", self.slug)

    def video_voice(self) -> str:
        return self.brand.get("video_voice", "Brian (American, deep)")

    def website(self) -> str:
        return self.brand.get("website", "")

    def default_facebook_page(self) -> str:
        return self._default_facebook_page or next(iter(self.facebook_pages), None)

    def default_hashtags(self) -> list:
        return self.brand.get("default_hashtags", [])

    def account_id(self, platform: str) -> str:
        return self.accounts[platform]["account_id"]

    def blotato_base_url(self) -> str:
        return "https://backend.blotato.com/v2"


def load_client(slug: str) -> ClientConfig:
    """Load a client config by slug (e.g. 'ryan')."""
    path = os.path.join(CLIENTS_DIR, f"{slug}.json")
    if not os.path.exists(path):
        available = list_client_slugs()
        raise FileNotFoundError(
            f"No client config found for '{slug}'. Available: {available}"
        )

    with open(path) as f:
        data = json.load(f)

    # Resolve API key  - prefer env var indirection for security
    api_key_env = data.get("blotato_api_key_env")
    api_key = (
        os.getenv(api_key_env, "") if api_key_env
        else data.get("blotato_api_key", "")
    )
    if not api_key:
        raise ValueError(
            f"Blotato API key not found for client '{slug}'. "
            f"Set the env var '{api_key_env}' or add 'blotato_api_key' to the JSON."
        )

    # Resolve service account path relative to project root (fallback auth)
    sa_file = data["drive"].get("service_account_file", "service_account.json")
    if not os.path.isabs(sa_file):
        sa_file = os.path.join(PROJECT_ROOT, sa_file)

    # Resolve OAuth token file path (preferred auth for personal accounts)
    token_file = data["drive"].get("token_file", f"tokens/{data['slug']}_token.json")
    if not os.path.isabs(token_file):
        token_file = os.path.join(PROJECT_ROOT, token_file)

    return ClientConfig(
        name=data["name"],
        slug=data["slug"],
        blotato_api_key=api_key,
        drive_content_folder_id=data["drive"]["content_folder_id"],
        drive_knowledge_base_folder_id=data["drive"]["knowledge_base_folder_id"],
        drive_service_account_file=sa_file,
        drive_token_file=token_file,
        accounts=data.get("accounts", {}),
        linkedin_pages=data.get("linkedin_pages", {}),
        facebook_pages=data.get("facebook_pages", {}),
        brand=data.get("brand", {}),
        visual_templates=data.get("visual_templates", {}),
        _default_facebook_page=data.get("default_facebook_page", ""),
    )


def list_client_slugs() -> list:
    """Return slugs of all configured clients."""
    if not os.path.isdir(CLIENTS_DIR):
        return []
    return [
        f[:-5] for f in os.listdir(CLIENTS_DIR)
        if f.endswith(".json")
    ]


def list_clients() -> list[dict]:
    """Return basic info for all clients."""
    result = []
    for slug in sorted(list_client_slugs()):
        try:
            path = os.path.join(CLIENTS_DIR, f"{slug}.json")
            with open(path) as f:
                data = json.load(f)
            result.append({"slug": slug, "name": data.get("name", slug)})
        except Exception:
            result.append({"slug": slug, "name": slug})
    return result

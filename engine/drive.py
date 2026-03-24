"""
Google Drive access using a ClientConfig instead of global config.py.

Authentication supports two modes (auto-detected per client config):
  1. OAuth2 user token  - recommended for personal accounts ([YOUR NAME], [CLIENT NAME]).
     Requires a token.json file created by the one-time `setup_oauth.py` script.
  2. Service account    - for server/headless deployments with a JSON key file.

The engine checks for `drive_token_file` first, then falls back to
`drive_service_account_file`.
"""
from typing import Optional
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io
import os
import json

from engine.client_config import ClientConfig

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def _service(cfg: ClientConfig):
    """
    Build a Drive API service using the best available credential for this client.
    Priority: OAuth token file > service account file.
    """
    token_file = getattr(cfg, "drive_token_file", None)
    sa_file = getattr(cfg, "drive_service_account_file", None)

    # --- OAuth2 user token (preferred for personal accounts) ---
    if token_file and os.path.exists(token_file):
        with open(token_file) as f:
            token_data = json.load(f)
        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=SCOPES,
        )
        # Auto-refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist the refreshed token
            updated = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "token_uri": creds.token_uri,
            }
            with open(token_file, "w") as f:
                json.dump(updated, f, indent=2)
        return build("drive", "v3", credentials=creds)

    # --- Service account fallback ---
    if sa_file and os.path.exists(sa_file):
        creds = service_account.Credentials.from_service_account_file(
            sa_file, scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)

    raise RuntimeError(
        f"[Drive] No credentials found for client '{cfg.slug}'. "
        f"Run setup_oauth.py --client {cfg.slug} to authenticate."
    )


def _list_children(cfg: ClientConfig, folder_id: str, mime_filter: str = None) -> list:
    svc = _service(cfg)
    q = f"'{folder_id}' in parents and trashed=false"
    if mime_filter:
        q += f" and mimeType='{mime_filter}'"
    result = svc.files().list(
        q=q, pageSize=50,
        fields="files(id, name, mimeType, modifiedTime)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        orderBy="name",
    ).execute()
    return result.get("files", [])


def _read_doc(cfg: ClientConfig, file_id: str, mime_type: str = None) -> str:
    svc = _service(cfg)
    try:
        if mime_type == "application/vnd.google-apps.document":
            content = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
        else:
            content = svc.files().get_media(fileId=file_id).execute()
        return content.decode("utf-8") if isinstance(content, bytes) else content
    except HttpError as e:
        print(f"[Drive] Error reading {file_id}: {e}")
        return ""


def _week_number(name: str) -> int:
    parts = name.lower().replace("week", "").strip().split()
    try:
        return int(parts[0])
    except (IndexError, ValueError):
        return 999


def list_week_folders(cfg: ClientConfig) -> list:
    folders = _list_children(
        cfg, cfg.drive_content_folder_id,
        mime_filter="application/vnd.google-apps.folder",
    )
    week_folders = [f for f in folders if f["name"].lower().startswith("week")]
    week_folders.sort(key=lambda f: _week_number(f["name"]))
    return week_folders


def get_current_week_folder(cfg: ClientConfig) -> Optional[dict]:
    folders = list_week_folders(cfg)
    return folders[-1] if folders else None


def get_week_folder_by_name(cfg: ClientConfig, week: str) -> Optional[dict]:
    folders = list_week_folders(cfg)
    return next((f for f in folders if f["name"].lower() == week.lower()), None)


def load_week_content_files(cfg: ClientConfig, folder: dict) -> list:
    """Return list of (filename, raw_text) tuples from a week folder."""
    files = _list_children(cfg, folder["id"])
    results = []
    for f in files:
        if f["mimeType"] in DOC_MIME_TYPES:
            text = _read_doc(cfg, f["id"], mime_type=f["mimeType"])
            if text:
                results.append((f["name"], text))
    results.sort(key=lambda x: x[0])
    return results


DOC_MIME_TYPES = {
    "application/vnd.google-apps.document",
    "text/plain",
    "text/markdown",
}
IMAGE_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}


def get_client_knowledge(cfg: ClientConfig) -> str:
    """Read all docs from the client knowledge base folder."""
    folder_id = cfg.drive_knowledge_base_folder_id
    if not folder_id:
        return ""
    files = _list_children(cfg, folder_id)
    parts = []
    for f in files:
        if f["mimeType"] in DOC_MIME_TYPES:
            text = _read_doc(cfg, f["id"], mime_type=f["mimeType"])
            if text:
                parts.append(f"### {f['name']}\n{text.strip()}")
        elif f["mimeType"] == "application/vnd.google-apps.folder":
            for sf in _list_children(cfg, f["id"]):
                if sf["mimeType"] in DOC_MIME_TYPES:
                    text = _read_doc(cfg, sf["id"], mime_type=sf["mimeType"])
                    if text:
                        parts.append(f"### {f['name']} / {sf['name']}\n{text.strip()}")
    return "\n\n---\n\n".join(parts)


def get_brand_images(cfg: ClientConfig, download_dir: str = None) -> list:
    """Download brand images from Week 1. Returns list of local file paths."""
    if download_dir is None:
        download_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            f"brand_images_{cfg.slug}"
        )
    folders = list_week_folders(cfg)
    if not folders:
        return []
    week1 = folders[0]
    os.makedirs(download_dir, exist_ok=True)
    files = _list_children(cfg, week1["id"])
    images = [f for f in files if f["mimeType"] in IMAGE_MIME_TYPES]

    svc = _service(cfg)
    paths = []
    for img in images:
        ext = img["mimeType"].split("/")[-1]
        dest = os.path.join(
            download_dir,
            img["name"] if "." in img["name"] else f"{img['name']}.{ext}"
        )
        try:
            request = svc.files().get_media(fileId=img["id"], supportsAllDrives=True)
            buf = io.BytesIO()
            dl = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = dl.next_chunk()
            with open(dest, "wb") as fh:
                fh.write(buf.getvalue())
            paths.append(dest)
        except HttpError as e:
            print(f"[Drive] Error downloading {img['name']}: {e}")
    return paths

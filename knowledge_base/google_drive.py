"""
Google Drive reader  - uses a service account for headless, automated access.
No browser login required.

Service account: your-service-account@your-project.iam.gserviceaccount.com
Credentials file: service_account.json (in project root)

IMPORTANT: The service account must be granted access to each Drive folder.
Share the following folders with the service account email above (Viewer is enough):
  - Content folder:       https://drive.google.com/drive/folders/YOUR_DRIVE_FOLDER_ID
  - Knowledge base:       https://drive.google.com/drive/folders/0APmCUWwWZsQIUk9PVA

Two Drive sources:
1. Content folder (CONTENT_FOLDER_ID):
     Week 1/  - published, contains brand template images
     Week 2/  - current week, Manus-generated content docs
     Week N/  - future weeks

2. Knowledge base (KNOWLEDGE_BASE_FOLDER_ID):
     Docs about [YOUR NAME]  - author profile, voice, expertise, brand guidelines.
     Injected into every post so content always sounds like [YOUR NAME].
"""
import io
import os
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

import config

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "service_account.json"
)

IMAGE_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}
DOC_MIME_TYPES = {
    "application/vnd.google-apps.document",
    "text/plain",
    "text/markdown",
}


def _service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _list_children(folder_id: str, mime_filter: str = None) -> list[dict]:
    """List immediate children of a folder."""
    svc = _service()
    q = f"'{folder_id}' in parents and trashed=false"
    if mime_filter:
        q += f" and mimeType='{mime_filter}'"
    result = svc.files().list(
        q=q,
        pageSize=50,
        fields="files(id, name, mimeType, modifiedTime)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        orderBy="name",
    ).execute()
    return result.get("files", [])


def list_week_folders() -> list[dict]:
    """Return all Week N folders inside the content root, sorted by week number."""
    folders = _list_children(
        config.CONTENT_FOLDER_ID,
        mime_filter="application/vnd.google-apps.folder",
    )
    week_folders = [f for f in folders if f["name"].lower().startswith("week")]
    week_folders.sort(key=lambda f: _week_number(f["name"]))
    return week_folders


def _week_number(name: str) -> int:
    parts = name.lower().replace("week", "").strip().split()
    try:
        return int(parts[0])
    except (IndexError, ValueError):
        return 999


def get_current_week_folder() -> Optional[dict]:
    """Return the highest-numbered week folder (the active one)."""
    folders = list_week_folders()
    return folders[-1] if folders else None


def get_week1_folder() -> Optional[dict]:
    """Return the Week 1 folder (brand template source)."""
    folders = list_week_folders()
    return folders[0] if folders else None


def read_doc_content(file_id: str, mime_type: str = None) -> str:
    """Export a Google Doc or plain text file as a string."""
    svc = _service()
    try:
        if mime_type == "application/vnd.google-apps.document":
            content = svc.files().export(
                fileId=file_id, mimeType="text/plain"
            ).execute()
        else:
            content = svc.files().get_media(fileId=file_id).execute()
        return content.decode("utf-8") if isinstance(content, bytes) else content
    except HttpError as e:
        print(f"[Drive] Error reading {file_id}: {e}")
        return ""


def download_image(file_id: str, dest_path: str) -> Optional[str]:
    """Download an image file to dest_path. Returns the path or None on failure."""
    svc = _service()
    try:
        request = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        with open(dest_path, "wb") as f:
            f.write(buf.getvalue())
        return dest_path
    except HttpError as e:
        print(f"[Drive] Error downloading image {file_id}: {e}")
        return None


def read_folder_content(folder: dict) -> str:
    """Read all content docs from a given folder dict and return as a single string."""
    files = _list_children(folder["id"])
    content_parts = []
    for f in files:
        if f["mimeType"] in DOC_MIME_TYPES:
            text = read_doc_content(f["id"], mime_type=f["mimeType"])
            if text:
                content_parts.append(f"### {f['name']}\n{text.strip()}")
    if not content_parts:
        print(f"[Drive] No content docs found in {folder['name']}.")
    return "\n\n---\n\n".join(content_parts)


def load_week_content_files(folder: dict) -> list[tuple]:
    """
    Load all content files from a week folder.
    Returns list of (filename, raw_text) tuples, sorted by filename.
    Skips zip files and non-content types.
    """
    files = _list_children(folder["id"])
    results = []
    for f in files:
        if f["mimeType"] in DOC_MIME_TYPES:
            text = read_doc_content(f["id"], mime_type=f["mimeType"])
            if text:
                results.append((f["name"], text))
    results.sort(key=lambda x: x[0])
    return results


def get_current_week_content() -> str:
    """
    Read all content docs from the current week folder.
    Returns them as a single string for the LinkedIn post builder.
    """
    folder = get_current_week_folder()
    if not folder:
        print("[Drive] No week folders found in content root.")
        return ""

    print(f"[Drive] Reading content from: {folder['name']}")
    files = _list_children(folder["id"])

    content_parts = []
    for f in files:
        if f["mimeType"] in DOC_MIME_TYPES:
            text = read_doc_content(f["id"], mime_type=f["mimeType"])
            if text:
                content_parts.append(f"### {f['name']}\n{text.strip()}")

    if not content_parts:
        print(f"[Drive] No content docs found in {folder['name']}.")
    return "\n\n---\n\n".join(content_parts)


def get_ryan_knowledge() -> str:
    """
    Read all docs from [YOUR NAME]'s knowledge base folder.
    Returns them as a single context string injected into every post.
    Folder: KNOWLEDGE_BASE_FOLDER_ID (0APmCUWwWZsQIUk9PVA)
    """
    folder_id = config.KNOWLEDGE_BASE_FOLDER_ID
    if not folder_id:
        print("[Drive] KNOWLEDGE_BASE_FOLDER_ID not set  - skipping author context.")
        return ""

    print("[Drive] Loading [YOUR NAME]'s knowledge base...")
    files = _list_children(folder_id)

    context_parts = []
    for f in files:
        if f["mimeType"] in DOC_MIME_TYPES:
            text = read_doc_content(f["id"], mime_type=f["mimeType"])
            if text:
                context_parts.append(f"### {f['name']}\n{text.strip()}")
        elif f["mimeType"] == "application/vnd.google-apps.folder":
            sub_files = _list_children(f["id"])
            for sf in sub_files:
                if sf["mimeType"] in DOC_MIME_TYPES:
                    text = read_doc_content(sf["id"], mime_type=sf["mimeType"])
                    if text:
                        context_parts.append(
                            f"### {f['name']} / {sf['name']}\n{text.strip()}"
                        )

    if not context_parts:
        print("[Drive] No docs found in knowledge base folder.")
        return ""

    print(f"[Drive] ✓ Knowledge base loaded ({len(context_parts)} doc(s))")
    return "\n\n---\n\n".join(context_parts)


def get_brand_images(download_dir: str = "brand_images") -> list[str]:
    """
    Download brand template images from Week 1 into download_dir.
    Returns list of local file paths.
    """
    folder = get_week1_folder()
    if not folder:
        print("[Drive] Week 1 folder not found  - no brand images loaded.")
        return []

    os.makedirs(download_dir, exist_ok=True)
    files = _list_children(folder["id"])
    images = [f for f in files if f["mimeType"] in IMAGE_MIME_TYPES]

    paths = []
    for img in images:
        ext = img["mimeType"].split("/")[-1]
        dest = os.path.join(
            download_dir,
            img["name"] if "." in img["name"] else f"{img['name']}.{ext}"
        )
        path = download_image(img["id"], dest)
        if path:
            paths.append(path)
            print(f"[Drive] Brand image downloaded: {img['name']}")

    return paths

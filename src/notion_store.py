import os

import requests

_SECRETS_FILE = os.path.expanduser("~/.secrets/voice2text-notion.env")
NOTION_VERSION = "2026-03-11"
_MAX_RICH_TEXT_CHARS = 2000
_MAX_BLOCKS_PER_REQUEST = 90


def _load_secret(name: str) -> str:
    if name in os.environ:
        return os.environ[name]
    if os.path.exists(_SECRETS_FILE):
        with open(_SECRETS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key == name:
                    return value
    raise RuntimeError(f"{name} not found in environment or {_SECRETS_FILE}")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_load_secret('NOTION_API_KEY')}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _chunk_text_to_paragraph_blocks(text: str) -> list:
    chunks = [
        text[i : i + _MAX_RICH_TEXT_CHARS]
        for i in range(0, len(text), _MAX_RICH_TEXT_CHARS)
    ] or [""]
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
        }
        for chunk in chunks
    ]


def _heading_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _append_blocks(page_id: str, blocks: list) -> None:
    for i in range(0, len(blocks), _MAX_BLOCKS_PER_REQUEST):
        batch = blocks[i : i + _MAX_BLOCKS_PER_REQUEST]
        response = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=_headers(),
            json={"children": batch},
            timeout=60,
        )
        response.raise_for_status()


_SHOW_DATABASE_SCHEMA = {
    "檔名": {"title": {}},
    "檔案大小": {"number": {}},
    "副檔名": {"rich_text": {}},
    "標題": {"rich_text": {}},
    "發布日期": {"date": {}},
    "狀態": {"status": {}},
    "分類": {"multi_select": {}},
    "重複偵測次數": {"number": {}},
    "音檔": {"files": {}},
}


def get_or_create_show_database(feed_page_id: str, name: str) -> str:
    page_response = requests.get(
        f"https://api.notion.com/v1/pages/{feed_page_id}",
        headers=_headers(),
        timeout=60,
    )
    page_response.raise_for_status()
    existing = page_response.json()["properties"]["集數資料庫ID"]["rich_text"]
    if existing:
        return existing[0]["plain_text"]

    create_response = requests.post(
        "https://api.notion.com/v1/databases",
        headers=_headers(),
        json={
            "parent": {"type": "page_id", "page_id": feed_page_id},
            "title": [{"type": "text", "text": {"content": name}}],
            "initial_data_source": {"properties": _SHOW_DATABASE_SCHEMA},
        },
        timeout=60,
    )
    create_response.raise_for_status()
    data_source_id = create_response.json()["data_sources"][0]["id"]

    update_response = requests.patch(
        f"https://api.notion.com/v1/pages/{feed_page_id}",
        headers=_headers(),
        json={
            "properties": {
                "集數資料庫ID": {
                    "rich_text": [{"type": "text", "text": {"content": data_source_id}}]
                }
            }
        },
        timeout=60,
    )
    update_response.raise_for_status()

    return data_source_id


def is_already_processed(data_source_id: str, filename: str, file_size: int, extension: str) -> bool:
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
        headers=_headers(),
        json={
            "filter": {
                "and": [
                    {"property": "檔名", "title": {"equals": filename}},
                    {"property": "檔案大小", "number": {"equals": file_size}},
                    {"property": "副檔名", "rich_text": {"equals": extension}},
                ]
            }
        },
        timeout=60,
    )
    response.raise_for_status()
    results = response.json()["results"]
    if not results:
        return False

    for existing in results:
        current_count = (
            existing["properties"].get("重複偵測次數", {}).get("number") or 0
        )
        update_response = requests.patch(
            f"https://api.notion.com/v1/pages/{existing['id']}",
            headers=_headers(),
            json={"properties": {"重複偵測次數": {"number": current_count + 1}}},
            timeout=60,
        )
        update_response.raise_for_status()

    return True


def is_filename_recorded(data_source_id: str, filename: str, extension: str) -> bool:
    """Cheap pre-check by filename+extension only, no file_size comparison —
    for RSS-sourced episodes whose feed doesn't reliably report a real file
    size, so callers can skip a download without needing one first."""
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
        headers=_headers(),
        json={
            "filter": {
                "and": [
                    {"property": "檔名", "title": {"equals": filename}},
                    {"property": "副檔名", "rich_text": {"equals": extension}},
                ]
            }
        },
        timeout=60,
    )
    response.raise_for_status()
    return bool(response.json()["results"])


def _record_properties(
    filename: str,
    file_size: int,
    extension: str,
    tags: list,
    title: str = None,
    published_at: str = None,
) -> dict:
    properties = {
        "檔名": {"title": [{"type": "text", "text": {"content": filename}}]},
        "檔案大小": {"number": file_size},
        "副檔名": {"rich_text": [{"type": "text", "text": {"content": extension}}]},
        "狀態": {"status": {"name": "Done"}},
    }
    if tags:
        properties["分類"] = {"multi_select": [{"name": tag} for tag in tags]}
    if title:
        properties["標題"] = {"rich_text": [{"type": "text", "text": {"content": title}}]}
    if published_at:
        properties["發布日期"] = {"date": {"start": published_at}}
    return properties


def save_record(
    data_source_id: str,
    filename: str,
    file_size: int,
    extension: str,
    transcript: str,
    report: str,
    tags: list = None,
    title: str = None,
    published_at: str = None,
) -> str:
    create_response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(),
        json={
            "parent": {
                "type": "data_source_id",
                "data_source_id": data_source_id,
            },
            "properties": _record_properties(
                filename, file_size, extension, tags, title, published_at
            ),
        },
        timeout=60,
    )
    create_response.raise_for_status()
    page_id = create_response.json()["id"]

    blocks = (
        [_heading_block("逐字稿")]
        + _chunk_text_to_paragraph_blocks(transcript)
        + [_heading_block("整理報告")]
        + _chunk_text_to_paragraph_blocks(report)
    )
    _append_blocks(page_id, blocks)

    return page_id


def update_record(
    page_id: str,
    filename: str,
    file_size: int,
    extension: str,
    transcript: str,
    report: str,
    tags: list = None,
    title: str = None,
    published_at: str = None,
) -> None:
    update_response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={
            "properties": _record_properties(
                filename, file_size, extension, tags, title, published_at
            )
        },
        timeout=60,
    )
    update_response.raise_for_status()

    blocks = (
        [_heading_block("逐字稿")]
        + _chunk_text_to_paragraph_blocks(transcript)
        + [_heading_block("整理報告")]
        + _chunk_text_to_paragraph_blocks(report)
    )
    _append_blocks(page_id, blocks)


def list_pending_uploads(data_source_id: str) -> list:
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
        headers=_headers(),
        json={
            "filter": {
                "and": [
                    {"property": "音檔", "files": {"is_not_empty": True}},
                    {"property": "狀態", "status": {"does_not_equal": "Done"}},
                ]
            }
        },
        timeout=60,
    )
    response.raise_for_status()

    pending = []
    for page in response.json()["results"]:
        files = page["properties"]["音檔"]["files"]
        if not files:
            continue
        pending.append(
            {
                "page_id": page["id"],
                "filename": files[0]["name"],
                "file_url": files[0]["file"]["url"],
            }
        )
    return pending


def fetch_record(page_id: str) -> dict:
    page_response = requests.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        timeout=60,
    )
    page_response.raise_for_status()
    props = page_response.json()["properties"]
    filename = props["檔名"]["title"][0]["plain_text"] if props["檔名"]["title"] else ""
    file_size = props["檔案大小"]["number"]
    extension_rt = props["副檔名"]["rich_text"]
    extension = extension_rt[0]["plain_text"] if extension_rt else ""
    duplicate_count = props.get("重複偵測次數", {}).get("number") or 0
    tags = [t["name"] for t in props.get("分類", {}).get("multi_select", [])]
    title_rt = props.get("標題", {}).get("rich_text", [])
    title = title_rt[0]["plain_text"] if title_rt else ""
    published_at = (props.get("發布日期", {}).get("date") or {}).get("start")

    blocks_response = requests.get(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=_headers(),
        params={"page_size": 100},
        timeout=60,
    )
    blocks_response.raise_for_status()
    blocks = blocks_response.json()["results"]

    sections = {"逐字稿": [], "整理報告": []}
    current_section = None
    for block in blocks:
        if block["type"] == "heading_2":
            text = "".join(
                rt["plain_text"] for rt in block["heading_2"]["rich_text"]
            )
            current_section = text if text in sections else None
        elif block["type"] == "paragraph" and current_section:
            text = "".join(
                rt["plain_text"] for rt in block["paragraph"]["rich_text"]
            )
            sections[current_section].append(text)

    return {
        "filename": filename,
        "file_size": file_size,
        "extension": extension,
        "duplicate_count": duplicate_count,
        "tags": tags,
        "title": title,
        "published_at": published_at,
        "transcript": "".join(sections["逐字稿"]),
        "report": "".join(sections["整理報告"]),
    }

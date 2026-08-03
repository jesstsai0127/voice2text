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


def is_already_processed(filename: str, file_size: int, extension: str) -> bool:
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{_load_secret('NOTION_DATA_SOURCE_ID')}/query",
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


def _record_properties(
    filename: str,
    file_size: int,
    extension: str,
    tags: list,
    title: str = None,
    source_page_id: str = None,
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
    if source_page_id:
        properties["來源"] = {"relation": [{"id": source_page_id}]}
    return properties


def save_record(
    filename: str,
    file_size: int,
    extension: str,
    transcript: str,
    report: str,
    tags: list = None,
    title: str = None,
    source_page_id: str = None,
) -> str:
    create_response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(),
        json={
            "parent": {
                "type": "data_source_id",
                "data_source_id": _load_secret("NOTION_DATA_SOURCE_ID"),
            },
            "properties": _record_properties(
                filename, file_size, extension, tags, title, source_page_id
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
    source_page_id: str = None,
) -> None:
    update_response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={
            "properties": _record_properties(
                filename, file_size, extension, tags, title, source_page_id
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


def list_pending_uploads() -> list:
    response = requests.post(
        f"https://api.notion.com/v1/data_sources/{_load_secret('NOTION_DATA_SOURCE_ID')}/query",
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
    source_relations = props.get("來源", {}).get("relation", [])
    source_page_id = source_relations[0]["id"] if source_relations else None

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
        "source_page_id": source_page_id,
        "transcript": "".join(sections["逐字稿"]),
        "report": "".join(sections["整理報告"]),
    }

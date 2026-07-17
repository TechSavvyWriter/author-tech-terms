"""
Sync Tech Terms from ClickUp to terms.json.

Reads all tasks from the configured ClickUp List, filters to Published,
transforms them into a clean public JSON structure, and writes to data/terms.json.

Environment variables required:
  CLICKUP_API_TOKEN  - Personal API token from ClickUp
  CLICKUP_LIST_ID    - ID of the Tech Terms Explained list

Optional:
  OUTPUT_PATH        - Where to write JSON (default: data/terms.json)
"""

import json
import os
import sys
from pathlib import Path

import requests

CLICKUP_API_BASE = "https://api.clickup.com/api/v2"

# Custom field names as they appear in ClickUp — used to auto-discover field IDs.
# These MUST match the field names in your ClickUp list exactly.
FIELD_NAMES = {
    "slug": "Slug",
    "letter": "Letter",
    "plain_english": "Plain English",
    "tech_speak": "Tech Speak",
    "example": "Example",
    "recommendation": "Recommendation",
    "long_definition": "Long Definition",
    "category": "Category",
    "related_terms": "Related Terms",
    "related_dotthq_tool": "Related DottHQ Tool",
    # Member Notes deliberately excluded — never leaves ClickUp via this script.
}

PUBLISHED_STATUS = "published"  # ClickUp lowercases status names in the API


def get_env(name: str) -> str:
    """Read a required environment variable or exit with a clear error."""
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def fetch_all_tasks(list_id: str, token: str) -> list[dict]:
    """Fetch every task in the list, handling pagination."""
    headers = {"Authorization": token}
    all_tasks = []
    page = 0

    while True:
        url = f"{CLICKUP_API_BASE}/list/{list_id}/task"
        params = {
            "page": page,
            "include_closed": "true",  # in case Published is treated as closed
            "subtasks": "false",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        tasks = data.get("tasks", [])

        if not tasks:
            break

        all_tasks.extend(tasks)
        # ClickUp returns 100 per page. If fewer, we're done.
        if len(tasks) < 100:
            break
        page += 1

    return all_tasks


def extract_custom_field(task: dict, field_name: str) -> str:
    """Pull a custom field's value from a task by field name."""
    for field in task.get("custom_fields", []):
        if field.get("name") == field_name:
            value = field.get("value")
            if value is None:
                return ""

            # Dropdowns return an option index (int); resolve to the option name.
            field_type = field.get("type")
            if field_type == "drop_down":
                options = field.get("type_config", {}).get("options", [])
                # value is the orderindex (int) OR the option UUID (str)
                for opt in options:
                    if opt.get("orderindex") == value or opt.get("id") == value:
                        return opt.get("name", "")
                return ""

            # Labels field returns list of option IDs
            if field_type == "labels":
                options = field.get("type_config", {}).get("options", [])
                if isinstance(value, list):
                    names = []
                    for v in value:
                        for opt in options:
                            if opt.get("id") == v:
                                names.append(opt.get("label", ""))
                    return ",".join(names)

            # Text-like fields return the value directly
            return str(value)
    return ""


def transform_task(task: dict) -> dict:
    """Transform a ClickUp task into a clean public term dict."""
    return {
        "term": task.get("name", "").strip(),
        "slug": extract_custom_field(task, FIELD_NAMES["slug"]),
        "letter": extract_custom_field(task, FIELD_NAMES["letter"]),
        "plain_english": extract_custom_field(task, FIELD_NAMES["plain_english"]),
        "tech_speak": extract_custom_field(task, FIELD_NAMES["tech_speak"]),
        "example": extract_custom_field(task, FIELD_NAMES["example"]),
        "recommendation": extract_custom_field(task, FIELD_NAMES["recommendation"]),
        "long_definition": extract_custom_field(task, FIELD_NAMES["long_definition"]),
        "category": extract_custom_field(task, FIELD_NAMES["category"]),
        "related_terms": [
            s.strip()
            for s in extract_custom_field(task, FIELD_NAMES["related_terms"]).split(",")
            if s.strip()
        ],
        "related_dotthq_tool": extract_custom_field(
            task, FIELD_NAMES["related_dotthq_tool"]
        ),
    }


def is_published(task: dict) -> bool:
    """Check whether a task's status is Published."""
    status = task.get("status", {})
    if isinstance(status, dict):
        return status.get("status", "").lower() == PUBLISHED_STATUS
    return str(status).lower() == PUBLISHED_STATUS


def main() -> None:
    token = get_env("CLICKUP_API_TOKEN")
    list_id = get_env("CLICKUP_LIST_ID")
    output_path = Path(os.environ.get("OUTPUT_PATH", "data/terms.json"))

    print(f"Fetching tasks from ClickUp list {list_id}...")
    tasks = fetch_all_tasks(list_id, token)
    print(f"  Fetched {len(tasks)} tasks total.")

    published = [t for t in tasks if is_published(t)]
    print(f"  {len(published)} are Published.")

    terms = [transform_task(t) for t in published]
    # Sort alphabetically by term name (case-insensitive)
    terms.sort(key=lambda t: t["term"].lower())

    # Build the final structure
    from datetime import datetime, timezone

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(terms),
        "terms": terms,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(terms)} terms to {output_path}")


if __name__ == "__main__":
    main()

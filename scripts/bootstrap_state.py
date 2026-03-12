from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SITE_MAP_PATH = DATA_DIR / "site_map.json"
STATE_PATH = DATA_DIR / "product_state.json"
POST_QUEUE_PATH = DATA_DIR / "post_queue.json"
RECHECK_QUEUE_PATH = DATA_DIR / "recheck_queue.json"
RUN_LOGS_DIR = DATA_DIR / "run_logs"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_product(product: dict[str, Any], category: str) -> dict[str, Any]:
    amazon_url = product.get("links", {}).get("amazon", "")
    site_url = product.get("links", {}).get("site", "")
    return {
        "id": product["id"],
        "slug": product["slug"],
        "title": product.get("title", ""),
        "category": category,
        "amazon_url": amazon_url,
        "site_url": site_url,
        "page_path": product.get("page", {}).get("path", ""),
        "catalog_path": f"{category}/products.json",
        "image": product.get("card", {}).get("image", ""),
        "status": "live",
        "archived": False,
        "restored": False,
        "last_checked": None,
        "last_seen_in_stock": None,
        "last_posted": None,
        "archive_reason": None,
        "archive_notes": None,
        "archive_history": [],
        "restore_history": [],
        "post_history": [],
        "check_history": [],
        "dedupe": {
            "stable_product_id": product["id"],
            "amazon_url": amazon_url,
            "site_url": site_url,
            "slug": product["slug"],
        },
        "copy_qa": {
            "last_checked": None,
            "status": "unknown",
            "notes": [],
        },
        "source": {
            "import_method": "existing_repo_inventory",
            "discovered_at": None,
            "imported_at": None,
        },
        "timestamps": {
            "created_at": now_iso(),
            "updated_at": now_iso(),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    site_map = load_json(SITE_MAP_PATH)
    inventory: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for category in site_map["site"]["structure"]["categories"]:
        category_slug = category["slug"]
        for product in category["products"]:
            product_id = product["id"]
            if product_id in seen_ids:
                raise ValueError(f"Duplicate product id detected: {product_id}")
            seen_ids.add(product_id)
            inventory.append(normalize_product(product, category_slug))

    state = {
        "generated_at": now_iso(),
        "source": "scripts/bootstrap_state.py",
        "schema_version": 1,
        "inventory": inventory,
        "stats": {
            "total_products": len(inventory),
            "live": len(inventory),
            "archived": 0,
            "restored": 0,
        },
        "rules": {
            "archive_policy": "conservative",
            "restore_policy": "preserve archived record and reactivate page metadata when confirmed in stock",
            "dedupe_key": "stable_product_id",
        },
    }

    post_queue = {
        "generated_at": now_iso(),
        "schema_version": 1,
        "cycle": {
            "order": ["product", "opinion", "product", "roundup"],
            "current_index": 0,
        },
        "items": [],
    }

    recheck_queue = {
        "generated_at": now_iso(),
        "schema_version": 1,
        "items": [],
    }

    RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(STATE_PATH, state)
    write_json(POST_QUEUE_PATH, post_queue)
    write_json(RECHECK_QUEUE_PATH, recheck_queue)
    print(f"Wrote {STATE_PATH.relative_to(ROOT)} with {len(inventory)} inventory records.")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import requests
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product_pipeline import ALLOWED_CATEGORIES, HEADERS, clean_text, extract_dynamic_images, extract_title, guess_category
DATA_DIR = ROOT / "data"
STATE_PATH = DATA_DIR / "product_state.json"
PROPOSAL_PATH = DATA_DIR / "proposal_queue.json"
DEFAULT_QUERIES = [
    "new zealand gift",
    "kiwi gift",
    "new zealand honey gift",
    "new zealand chocolate gift",
    "new zealand book",
    "greenstone necklace new zealand",
]
SEARCH_URL_TEMPLATE = "https://www.amazon.com/s?k={query}"
MAX_RESULTS_PER_QUERY = 8


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


_ASIN_PATTERNS = [
    re.compile(r"/dp/([A-Z0-9]{10})(?:[/?]|$)", re.I),
    re.compile(r"/gp/product/([A-Z0-9]{10})(?:[/?]|$)", re.I),
]


def extract_asin(url: str) -> str | None:
    for pattern in _ASIN_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1).upper()
    return None


def canonical_amazon_url(url: str) -> str:
    asin = extract_asin(url)
    if asin:
        return f"https://www.amazon.com/dp/{asin}"
    return url.split("?", 1)[0]


def load_product_state() -> dict[str, Any]:
    return load_json(STATE_PATH)


def load_or_create_proposals() -> dict[str, Any]:
    if PROPOSAL_PATH.exists():
        return load_json(PROPOSAL_PATH)
    return {
        "generated_at": now_iso(),
        "schema_version": 1,
        "items": [],
        "stats": {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "archived": 0,
            "imported": 0,
        },
        "search_queries": DEFAULT_QUERIES,
        "run_history": [],
    }


def existing_inventory_keys(state: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for item in state.get("inventory", []):
        for candidate in [item.get("amazon_url"), item.get("dedupe", {}).get("amazon_url")]:
            if candidate:
                keys.add(canonical_amazon_url(candidate))
        asin = extract_asin(item.get("amazon_url", ""))
        if asin:
            keys.add(f"asin:{asin}")
    return keys


def proposal_keys(queue: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for item in queue.get("items", []):
        if item.get("canonical_url"):
            keys.add(item["canonical_url"])
        if item.get("asin"):
            keys.add(f"asin:{item['asin']}")
    return keys


def fetch_search_html(query: str) -> str:
    url = SEARCH_URL_TEMPLATE.format(query=quote_plus(query))
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def extract_search_result_urls(raw_html: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]+)"', raw_html)
    product_urls: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        if "/dp/" not in href and "/gp/product/" not in href:
            continue
        url = urljoin("https://www.amazon.com", href)
        canonical = canonical_amazon_url(url)
        asin = extract_asin(canonical)
        if not asin:
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        product_urls.append(canonical)
        if len(product_urls) >= MAX_RESULTS_PER_QUERY:
            break
    return product_urls


def fetch_product_summary(url: str) -> dict[str, Any]:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    raw_html = response.text
    title = extract_title(raw_html)
    title = clean_text(title)
    images = extract_dynamic_images(raw_html)
    bullets = extract_bullets_from_html(raw_html)
    category = guess_category(title, bullets)
    unavailable_text = detect_unavailable_text(raw_html)
    return {
        "title": title,
        "image": images[0] if images else "",
        "category_guess": category if category in ALLOWED_CATEGORIES else "artwork",
        "availability": {
            "status": "out_of_stock" if unavailable_text else "unknown",
            "notes": unavailable_text,
        },
        "bullets": bullets[:3],
    }


def extract_bullets_from_html(raw_html: str) -> list[str]:
    bullets = re.findall(r'<span class="a-list-item">(.*?)</span>', raw_html, re.S)
    cleaned: list[str] = []
    for bullet in bullets:
        text = clean_text(bullet)
        if len(text) < 20:
            continue
        if text not in cleaned:
            cleaned.append(text)
    return cleaned[:5]


def detect_unavailable_text(raw_html: str) -> str | None:
    phrases = [
        "currently unavailable",
        "temporarily out of stock",
        "out of stock",
        "we don't know when or if this item will be back in stock",
    ]
    lowered = raw_html.lower()
    for phrase in phrases:
        if phrase in lowered:
            return phrase
    return None


def build_candidate(query: str, url: str, summary: dict[str, Any]) -> dict[str, Any]:
    asin = extract_asin(url)
    discovered_at = now_iso()
    proposal_status = "archived" if summary["availability"]["status"] == "out_of_stock" else "pending"
    return {
        "id": f"proposal/{asin or re.sub(r'[^a-z0-9]+', '-', url.lower()).strip('-')}",
        "asin": asin,
        "amazon_url": url,
        "canonical_url": canonical_amazon_url(url),
        "title": summary.get("title", ""),
        "category_guess": summary.get("category_guess", "artwork"),
        "image": summary.get("image", ""),
        "bullets": summary.get("bullets", []),
        "proposal_status": proposal_status,
        "inventory_status": summary.get("availability", {}).get("status", "unknown"),
        "search_query": query,
        "review_notes": summary.get("availability", {}).get("notes"),
        "review_history": [
            {
                "timestamp": discovered_at,
                "status": proposal_status,
                "reason": summary.get("availability", {}).get("notes") or "newly_discovered",
            }
        ],
        "source": {
            "type": "amazon_search",
            "discovered_at": discovered_at,
            "last_seen_at": discovered_at,
        },
        "timestamps": {
            "created_at": discovered_at,
            "updated_at": discovered_at,
            "proposed_at": discovered_at,
            "approved_at": None,
            "rejected_at": None,
            "archived_at": discovered_at if proposal_status == "archived" else None,
            "imported_at": None,
        },
        "dedupe": {
            "canonical_url": canonical_amazon_url(url),
            "asin": asin,
        },
    }


def refresh_stats(queue: dict[str, Any]) -> None:
    counts = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "archived": 0,
        "imported": 0,
    }
    for item in queue.get("items", []):
        status = item.get("proposal_status")
        if status in counts:
            counts[status] += 1
    queue["stats"] = counts
    queue["generated_at"] = now_iso()


def run_discovery(queries: list[str], limit: int) -> dict[str, Any]:
    state = load_product_state()
    queue = load_or_create_proposals()
    inventory_seen = existing_inventory_keys(state)
    proposal_seen = proposal_keys(queue)
    new_items: list[dict[str, Any]] = []
    run_record: dict[str, Any] = {
        "timestamp": now_iso(),
        "queries": queries,
        "new_items": 0,
        "skipped_existing_inventory": 0,
        "skipped_existing_proposals": 0,
        "errors": [],
    }

    for query in queries:
        if len(new_items) >= limit:
            break
        try:
            raw_html = fetch_search_html(query)
            urls = extract_search_result_urls(raw_html)
        except Exception as exc:
            run_record["errors"].append({"query": query, "stage": "search", "error": str(exc)})
            continue

        for url in urls:
            if len(new_items) >= limit:
                break
            canonical = canonical_amazon_url(url)
            asin = extract_asin(canonical)
            if canonical in inventory_seen or (asin and f"asin:{asin}" in inventory_seen):
                run_record["skipped_existing_inventory"] += 1
                continue
            if canonical in proposal_seen or (asin and f"asin:{asin}" in proposal_seen):
                run_record["skipped_existing_proposals"] += 1
                continue
            try:
                summary = fetch_product_summary(canonical)
            except Exception as exc:
                run_record["errors"].append({"query": query, "stage": "product", "url": canonical, "error": str(exc)})
                continue

            item = build_candidate(query, canonical, summary)
            queue.setdefault("items", []).append(item)
            proposal_seen.add(canonical)
            if asin:
                proposal_seen.add(f"asin:{asin}")
            new_items.append(item)

    run_record["new_items"] = len(new_items)
    queue.setdefault("search_queries", queries)
    queue.setdefault("run_history", []).append(run_record)
    queue["run_history"] = queue["run_history"][-20:]
    refresh_stats(queue)
    write_json(PROPOSAL_PATH, queue)
    return {"new_items": new_items, "run_record": run_record, "proposal_path": str(PROPOSAL_PATH)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover Amazon candidates for NZ Gift Finder proposal review.")
    parser.add_argument("queries", nargs="*", help="Optional search queries to override the defaults")
    parser.add_argument("--limit", type=int, default=6, help="Maximum new proposals to add in one run")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queries = args.queries or DEFAULT_QUERIES
    result = run_discovery(queries, max(1, args.limit))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

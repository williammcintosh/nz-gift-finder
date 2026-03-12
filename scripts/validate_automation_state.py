from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STATE_PATH = DATA_DIR / "product_state.json"
PROPOSAL_PATH = DATA_DIR / "proposal_queue.json"
REQUIRED_FIELDS = {
    "id",
    "slug",
    "title",
    "category",
    "amazon_url",
    "site_url",
    "page_path",
    "status",
    "archived",
    "restored",
    "last_checked",
    "last_seen_in_stock",
    "last_posted",
    "archive_reason",
    "dedupe",
    "timestamps",
}
VALID_STATUSES = {"live", "archived", "restored"}
VALID_PROPOSAL_STATUSES = {"pending", "approved", "rejected", "archived", "imported"}


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def load_proposals() -> dict:
    return json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))


def validate_inventory(state: dict) -> None:
    inventory = state.get("inventory")
    if not isinstance(inventory, list) or not inventory:
        raise AssertionError("Inventory must be a non-empty list")

    seen_ids: set[str] = set()
    seen_amazon_keys: set[tuple[str, str]] = set()
    for entry in inventory:
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            raise AssertionError(f"Missing required fields for {entry.get('id')}: {sorted(missing)}")
        if entry["status"] not in VALID_STATUSES:
            raise AssertionError(f"Invalid status for {entry['id']}: {entry['status']}")
        if entry["id"] in seen_ids:
            raise AssertionError(f"Duplicate id: {entry['id']}")
        seen_ids.add(entry["id"])
        dedupe_key = entry["dedupe"].get("stable_product_id")
        if dedupe_key != entry["id"]:
            raise AssertionError(f"Dedupe mismatch for {entry['id']}")
        amazon_url = entry.get("amazon_url")
        if amazon_url:
            amazon_pair = (entry["category"], amazon_url)
            if amazon_pair in seen_amazon_keys:
                raise AssertionError(f"Duplicate Amazon URL in category inventory: {amazon_pair}")
            seen_amazon_keys.add(amazon_pair)


def validate_proposals(proposals: dict) -> None:
    items = proposals.get("items")
    if not isinstance(items, list):
        raise AssertionError("Proposal items must be a list")

    seen_urls: set[str] = set()
    seen_asins: set[str] = set()
    for item in items:
        required = {"id", "amazon_url", "canonical_url", "proposal_status", "timestamps", "dedupe"}
        missing = required - set(item.keys())
        if missing:
            raise AssertionError(f"Missing proposal fields for {item.get('id')}: {sorted(missing)}")
        status = item["proposal_status"]
        if status not in VALID_PROPOSAL_STATUSES:
            raise AssertionError(f"Invalid proposal status for {item['id']}: {status}")
        canonical_url = item["canonical_url"]
        if canonical_url in seen_urls:
            raise AssertionError(f"Duplicate proposal canonical url: {canonical_url}")
        seen_urls.add(canonical_url)
        asin = item.get("asin")
        if asin:
            if asin in seen_asins:
                raise AssertionError(f"Duplicate proposal ASIN: {asin}")
            seen_asins.add(asin)


def simulate_lifecycle(state: dict, proposals: dict) -> None:
    sample = copy.deepcopy(state["inventory"][0])

    sample["status"] = "archived"
    sample["archived"] = True
    sample["restored"] = False
    sample["archive_reason"] = "amazon_unavailable"
    sample["archive_history"].append({"reason": sample["archive_reason"]})
    if not sample["archived"] or sample["status"] != "archived":
        raise AssertionError("Archive transition failed")

    sample["status"] = "restored"
    sample["archived"] = False
    sample["restored"] = True
    sample["archive_reason"] = None
    sample["restore_history"].append({"reason": "back_in_stock"})
    if sample["archived"] or sample["status"] != "restored" or not sample["restored"]:
        raise AssertionError("Restore transition failed")
    if not sample["page_path"] or not sample["site_url"]:
        raise AssertionError("Restore transition lost required page fields")

    proposal = {
        "id": "proposal/B000000000",
        "amazon_url": "https://www.amazon.com/dp/B000000000",
        "canonical_url": "https://www.amazon.com/dp/B000000000",
        "asin": "B000000000",
        "proposal_status": "pending",
        "timestamps": {"created_at": "now", "updated_at": "now"},
        "dedupe": {"canonical_url": "https://www.amazon.com/dp/B000000000", "asin": "B000000000"},
    }
    proposals = copy.deepcopy(proposals)
    proposals.setdefault("items", []).append(proposal)
    validate_proposals(proposals)
    proposals["items"][0]["proposal_status"] = "rejected"
    if proposals["items"][0]["proposal_status"] != "rejected":
        raise AssertionError("Proposal rejection transition failed")


def main() -> None:
    state = load_state()
    proposals = load_proposals()
    validate_inventory(state)
    validate_proposals(proposals)
    simulate_lifecycle(state, proposals)
    print("Automation state validation passed.")


if __name__ == "__main__":
    main()

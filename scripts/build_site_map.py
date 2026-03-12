from __future__ import annotations

import json
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_PATH = DATA_DIR / "site_map.json"
CATEGORY_DIRS = [
    path.parent for path in sorted(ROOT.glob("*/products.json")) if path.parent.name != "data"
]
STATIC_PAGES = ["about", "contact", "privacy", "terms"]
AMAZON_LINK_RE = re.compile(r'href="(https?://[^\"]+)"', re.I)
META_DESC_RE = re.compile(
    r'<meta\s+name="description"\s+content="([^"]*)"\s*/?>', re.I | re.S
)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", text or "")).strip()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_title(html: str) -> str:
    match = TITLE_RE.search(html)
    return clean(match.group(1)) if match else ""


def extract_h1(html: str) -> str:
    match = H1_RE.search(html)
    return clean(match.group(1)) if match else ""


def extract_meta_description(html: str) -> str:
    match = META_DESC_RE.search(html)
    return clean(match.group(1)) if match else ""


def extract_amazon_links(html: str) -> list[str]:
    matches = [url for url in AMAZON_LINK_RE.findall(html) if "amazon." in url or "amzn.to" in url]
    seen: list[str] = []
    for url in matches:
        if url not in seen:
            seen.append(url)
    return seen


def stable_product_id(category: str, slug: str) -> str:
    return f"{category}/{slug}"


def build_category(category_dir: Path) -> dict[str, Any]:
    category = category_dir.name
    catalog_path = category_dir / "products.json"
    index_path = category_dir / "index.html"
    catalog = load_json(catalog_path)
    index_html = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

    products: list[dict[str, Any]] = []
    for position, item in enumerate(catalog, start=1):
        href = item.get("href", "")
        slug = item.get("slug") or Path(href).stem
        product_path = category_dir / href if href else category_dir / f"{slug}.html"
        product_html = product_path.read_text(encoding="utf-8") if product_path.exists() else ""
        amazon_links = extract_amazon_links(product_html)
        products.append(
            {
                "id": stable_product_id(category, slug),
                "slug": slug,
                "title": item.get("title", ""),
                "card": {
                    "href": rel(product_path) if product_path.exists() else rel(category_dir / href),
                    "image": item.get("image", ""),
                    "alt": item.get("alt", ""),
                    "sub": item.get("sub", ""),
                    "position": position,
                },
                "page": {
                    "path": rel(product_path) if product_path.exists() else rel(category_dir / href),
                    "exists": product_path.exists(),
                    "title_tag": extract_title(product_html),
                    "h1": extract_h1(product_html),
                    "meta_description": extract_meta_description(product_html),
                },
                "links": {
                    "amazon": amazon_links[0] if amazon_links else "",
                    "amazon_all": amazon_links,
                    "site": f"/{category}/{slug}.html",
                },
                "status": {
                    "archived": False,
                    "live": True,
                    "restored": False,
                },
            }
        )

    return {
        "slug": category,
        "label": category.title(),
        "index": {
            "path": rel(index_path),
            "title_tag": extract_title(index_html),
            "h1": extract_h1(index_html),
            "meta_description": extract_meta_description(index_html),
        },
        "products_json": rel(catalog_path),
        "cards_js": rel(category_dir / "cards.js") if (category_dir / "cards.js").exists() else None,
        "products": products,
    }


def build_static_page(path: Path) -> dict[str, Any]:
    html = path.read_text(encoding="utf-8")
    return {
        "path": rel(path),
        "title_tag": extract_title(html),
        "h1": extract_h1(html),
        "meta_description": extract_meta_description(html),
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    root_index = ROOT / "index.html"
    root_html = root_index.read_text(encoding="utf-8")
    categories = [build_category(path) for path in CATEGORY_DIRS]
    total_products = sum(len(category["products"]) for category in categories)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "scripts/build_site_map.py",
        "site": {
            "name": "NZ Gift Finder",
            "root": {
                "path": rel(root_index),
                "title_tag": extract_title(root_html),
                "h1": extract_h1(root_html),
                "meta_description": extract_meta_description(root_html),
            },
            "structure": {
                "categories": categories,
                "static_pages": [
                    build_static_page(ROOT / page / "index.html")
                    for page in STATIC_PAGES
                    if (ROOT / page / "index.html").exists()
                ],
            },
        },
        "summary": {
            "category_count": len(categories),
            "product_count": total_products,
            "static_page_count": len(STATIC_PAGES),
        },
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)} with {total_products} mapped products.")


if __name__ == "__main__":
    main()

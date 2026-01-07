# admin_app.py
# Local admin tool for nzgiftfinder.
# Uses templates/ folder so Python stays small.

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, render_template, send_from_directory
from openai import OpenAI

load_dotenv()

ROOT = Path.cwd()
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_ROOT = ROOT

ALLOWED_CATEGORIES = ["clothing", "jewelry", "skincare", "artwork"]

PORT = int(os.getenv("ADMIN_PORT", "5000"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))


def slugify(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "product"


def generate_full_html(template_html: str, fields: dict) -> str:
    if not client:
        raise ValueError("Missing OPENAI_API_KEY.")

    fields_json = json.dumps(fields, ensure_ascii=True, indent=2)
    user_content = (
        "You will be given\n"
        "1) TEMPLATE_HTML which you must preserve structurally\n"
        "2) FIELDS_JSON with product info\n\n"
        "Rules\n"
        "- Keep all tags, ids, class names, imports, and layout identical to TEMPLATE_HTML\n"
        "- Only edit the text content and attribute values that are product specific\n"
        "- Update title tag, meta description, meta keywords if present, image alt text, "
        "breadcrumb text, h1, intro, why section\n"
        "- Use NZ vibe and common usage in NZ\n"
        "- No repetitive phrasing\n"
        "- No selling contrasts\n"
        "- Output only the final HTML file, nothing else\n\n"
        "TEMPLATE_HTML:\n"
        f"<<<\n{template_html}\n>>>\n"
        "FIELDS_JSON:\n"
        f"<<<\n{fields_json}\n>>>\n"
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert copywriter and HTML editor for nzgiftfinder. "
                    "Output must be valid HTML only."
                ),
            },
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )

    return resp.choices[0].message.content.strip()


def clean_single_line(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def truncate_line(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return f"{text[: limit - 3].rstrip()}..."


def first_sentence(text: str) -> str:
    cleaned = clean_single_line(text)
    match = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)
    return match[0] if match else cleaned


def fallback_card_sub(intro: str) -> str:
    return truncate_line(first_sentence(intro), 50)


def extract_meta_description(html: str) -> str:
    match = re.search(
        r'<meta\s+name="description"\s+content="([^"]*)"\s*/?>',
        html,
        flags=re.I,
    )
    return match.group(1).strip() if match else ""


def validate_generated_html(html: str, amazon_link: str) -> None:
    required_snippets = [
        "<html",
        "</html>",
        '<link rel="stylesheet" href="../style.css"',
        '<script src="../app.js">',
        'id="mainProductImage"',
    ]
    missing = [snippet for snippet in required_snippets if snippet not in html]
    if missing:
        raise ValueError(f"Generated HTML missing required content: {missing}")
    if amazon_link not in html:
        raise ValueError("Generated HTML does not include the affiliate link.")
    if "Swanndri" in html:
        raise ValueError("Generated HTML still contains 'Swanndri' text.")

def load_products_catalog(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Invalid catalog format in {path.name}: expected a list.")
    return data


def write_products_catalog(path: Path, items: list[dict]) -> None:
    tmp_path = path.with_suffix(".json.tmp")
    backup_path = path.with_suffix(".json.bak")

    payload = json.dumps(items, indent=2, ensure_ascii=True)
    tmp_path.write_text(f"{payload}\n", encoding="utf-8")

    json.loads(tmp_path.read_text(encoding="utf-8"))

    if path.exists():
        shutil.copy2(path, backup_path)

    tmp_path.replace(path)


def upsert_product_catalog(path: Path, product: dict) -> None:
    items = load_products_catalog(path)
    slug = product.get("slug")
    items = [item for item in items if item.get("slug") != slug]
    items.insert(0, product)
    write_products_catalog(path, items)



def ensure_writable_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    test = path / ".write_test.tmp"
    try:
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
    except Exception as e:
        raise PermissionError(f"Cannot write to {path}. Fix permissions. Details: {e}")


@app.route("/style.css")
def style_css():
    # Reuse your existing root style.css for the admin UI.
    css = ROOT / "style.css"
    if not css.exists():
        return "style.css not found in repo root.", 404
    return send_from_directory(ROOT, "style.css")


@app.route("/", methods=["GET", "POST"])
def admin_form():
    message = ""
    ok = False

    if request.method == "POST":
        try:
            title = (request.form.get("title") or "").strip()
            category = (request.form.get("category") or "").strip().lower()
            amazon_link = (request.form.get("amazon_link") or "").strip()
            nz_note = (request.form.get("nz_note") or "").strip()

            image1 = (request.form.get("image1") or "").strip()
            image2 = (request.form.get("image2") or "").strip()
            image3 = (request.form.get("image3") or "").strip()
            image_alt = (request.form.get("image_alt") or "").strip()
            images = [u for u in [image1, image2, image3] if u]

            if not title:
                raise ValueError("Missing product title.")
            if category not in ALLOWED_CATEGORIES:
                raise ValueError(f"Category must be one of: {', '.join(ALLOWED_CATEGORIES)}")
            if not amazon_link:
                raise ValueError("Missing affiliate link.")
            if not images:
                raise ValueError("Add at least 1 image URL.")

            details_raw = (request.form.get("details") or "").strip()

            slug = slugify(title)
            out_dir = OUTPUT_ROOT / category
            ensure_writable_dir(out_dir)

            out_path = (out_dir / f"{slug}.html").resolve()
            catalog_path = out_dir / "products.json"

            # Block path trickery
            if OUTPUT_ROOT not in out_path.parents:
                raise PermissionError("Blocked path traversal attempt.")

            template_html = (TEMPLATES_DIR / "product_page.html").read_text(
                encoding="utf-8"
            )
            fields = {
                "title": title,
                "category": category,
                "amazon_link": amazon_link,
                "nz_note": nz_note,
                "details": details_raw,
                "images": images,
                "image1": images[0],
                "image_alt": image_alt or title,
                "slug": slug,
            }
            html = generate_full_html(template_html, fields)
            validate_generated_html(html, amazon_link)

            alt_text = image_alt or title
            meta_description = extract_meta_description(html)
            card_sub = fallback_card_sub(meta_description or title)
            product_entry = {
                "slug": slug,
                "href": f"{slug}.html",
                "image": images[0],
                "alt": alt_text,
                "title": title,
                "sub": card_sub,
            }

            out_path.write_text(html, encoding="utf-8")
            upsert_product_catalog(catalog_path, product_entry)

            ok = True
            message = f"Created <code>{out_path.relative_to(OUTPUT_ROOT)}</code>"

        except Exception as e:
            ok = False
            message = f"{type(e).__name__}: {e}"

    return render_template(
        "admin_form.html",
        categories=ALLOWED_CATEGORIES,
        message=message,
        ok=ok,
    )


if __name__ == "__main__":
    # Run from repo root: python admin_app.py
    app.run(host="127.0.0.1", port=PORT, debug=True)

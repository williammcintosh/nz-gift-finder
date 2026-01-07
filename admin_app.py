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


def ai_copy(
    title: str, category: str, nz_note: str, details: str
) -> tuple[str, str, str, str, str]:
    if not client:
        intro = f"{title} is a solid gift that’s easy to actually use. {nz_note}".strip()
        meta_description = clean_single_line(intro)
        meta_keywords = f"{title}, {category}, NZ gifts, New Zealand gifts"
        card_sub = fallback_card_sub(intro)
        return intro, details, meta_description, meta_keywords, card_sub

    prompt = (
        "You are writing for a New Zealand gift website.\n\n"
        "Write FIVE sections:\n"
        "1) A short intro paragraph.\n"
        "2) A bullet list of product details.\n"
        "3) A META_DESCRIPTION.\n"
        "4) A KEYWORDS list.\n\n"
        "5) A CARD_SUB line.\n\n"
        "Rules for intro:\n"
        "- 90 to 130 words\n"
        "- Plain language\n"
        "- Mention NZ vibe once\n"
        "- Do not mention Amazon\n\n"
        "Rules for META_DESCRIPTION:\n"
        "- 140 to 160 characters\n"
        "- First 90 characters must include the most relevant key phrases\n"
        "- Match client search intent (what they'd type to find this product)\n\n"
        "Rules for KEYWORDS:\n"
        "- 6 to 10 comma-separated keywords\n"
        "- Include the product type, style/theme, and New Zealand context\n\n"
        "Rules for CARD_SUB:\n"
        "- 50 characters max\n"
        "- Describes the product in a quick, helpful way\n\n"
        "Rules for details:\n"
        "- 4 to 7 bullet points\n"
        "- Practical info only\n"
        "- No marketing fluff\n\n"
        f"Product title: {title}\n"
        f"Category: {category}\n"
        f"NZ note: {nz_note}\n"
        f"Raw product details:\n{details}\n\n"
        "Return format:\n"
        "INTRO:\n<paragraph>\n\n"
        "DETAILS:\n- bullet\n- bullet\n"
        "\n\nMETA_DESCRIPTION:\n<single line>\n\n"
        "KEYWORDS:\nkeyword, keyword, keyword\n\n"
        "CARD_SUB:\n<short line>\n"
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    text = resp.choices[0].message.content.strip()

    def extract_section(label: str) -> str:
        pattern = rf"{label}:\s*(.*?)(?=\n[A-Z_]+:\s*|$)"
        match = re.search(pattern, text, flags=re.S)
        return match.group(1).strip() if match else ""

    intro = extract_section("INTRO")
    if not intro and "DETAILS:" in text:
        intro = text.split("DETAILS:")[0].replace("INTRO:", "").strip()
    if not intro:
        intro = text

    bullets = extract_section("DETAILS")
    meta_description = extract_section("META_DESCRIPTION")
    meta_keywords = extract_section("KEYWORDS")
    card_sub = extract_section("CARD_SUB")

    meta_description = clean_single_line(meta_description) if meta_description else ""
    if not meta_description:
        meta_description = clean_single_line(intro) or clean_single_line(title)

    if meta_keywords:
        meta_keywords = ", ".join(
            [kw.strip() for kw in meta_keywords.split(",") if kw.strip()]
        )
    if not meta_keywords:
        meta_keywords = f"{title}, {category}, NZ gifts, New Zealand gifts"

    if not card_sub:
        card_sub = fallback_card_sub(intro)
    else:
        card_sub = clean_single_line(card_sub)
        card_sub = truncate_line(card_sub, 50)

    return intro, bullets, meta_description, meta_keywords, card_sub


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
            intro, details_clean, meta_description, meta_keywords, card_sub = ai_copy(
                title, category, nz_note, details_raw
            )

            slug = slugify(title)
            out_dir = OUTPUT_ROOT / category
            ensure_writable_dir(out_dir)

            out_path = (out_dir / f"{slug}.html").resolve()
            catalog_path = out_dir / "products.json"

            # Block path trickery
            if OUTPUT_ROOT not in out_path.parents:
                raise PermissionError("Blocked path traversal attempt.")

            html = render_template(
                "product_page.html",
                title=title,
                category=category,
                intro=intro,
                why=nz_note,
                details=details_clean,
                amazon_link=amazon_link,
                images=images,
                image1=images[0],
                meta_description=meta_description,
                meta_keywords=meta_keywords,
            )

            if "Swanndri" in html:
                raise ValueError("Generated HTML still contains 'Swanndri' text.")

            alt_text = image_alt or title
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

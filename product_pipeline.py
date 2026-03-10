from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

import requests

ROOT = Path(__file__).resolve().parent
ALLOWED_CATEGORIES = ["artwork", "clothing", "jewelry", "skincare", "food", "books"]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def slugify(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "product"


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def normalize_affiliate_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    keep_order = [
        "tag",
        "linkCode",
        "linkId",
        "language",
        "ref_",
        "psc",
        "smid",
        "th",
    ]
    kept = []
    for key in keep_order:
        if key in query:
            for value in query[key]:
                kept.append(f"{key}={value}")
    query_str = "&".join(kept)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query_str, ""))


def extract_title(raw_html: str) -> str:
    match = re.search(r'id="productTitle"[^>]*>(.*?)</span>', raw_html, re.S)
    if match:
        return clean_text(match.group(1))
    match = re.search(r"<title>(.*?)</title>", raw_html, re.S | re.I)
    if match:
        title = clean_text(match.group(1))
        title = re.sub(r":\s*Amazon\..*$", "", title)
        return title
    return "NZ Gift"


def extract_dynamic_images(raw_html: str) -> list[str]:
    urls: list[str] = []
    match = re.search(r'data-a-dynamic-image="([^"]+)"', raw_html)
    if match:
        payload = html.unescape(match.group(1))
        try:
            data = json.loads(payload)
            urls.extend(data.keys())
        except Exception:
            pass
    if not urls:
        pattern = r"https://m\.media-amazon\.com/images/I/[A-Za-z0-9%+_,.-]+\.(?:jpg|jpeg|png|webp)"
        urls = re.findall(pattern, raw_html)
    unique: list[str] = []
    for url in urls:
        if url not in unique:
            unique.append(url)
    return unique[:6]


def extract_bullets(raw_html: str) -> list[str]:
    block = re.search(r'<div id="feature-bullets".*?</div>\s*</div>', raw_html, re.S)
    source = block.group(0) if block else raw_html
    bullets = re.findall(r'<span class="a-list-item">(.*?)</span>', source, re.S)
    cleaned = []
    banned_fragments = [
        "image unavailable",
        "publication date",
        "publisher",
        "language",
        "isbn",
        "best sellers rank",
        "customer reviews",
        "amazon",
        "ue.count",
        "topreviewsdetailpagecount",
        "review",
    ]
    for bullet in bullets:
        text = clean_text(bullet)
        low = text.lower()
        if len(text) < 20:
            continue
        if any(fragment in low for fragment in banned_fragments):
            continue
        if re.search(r"#\d+\s+in\s+", low):
            continue
        cleaned.append(text)
    deduped: list[str] = []
    for item in cleaned:
        if item not in deduped:
            deduped.append(item)
    return deduped[:5]


def guess_category(title: str, bullets: list[str]) -> str:
    hay = f"{title} {' '.join(bullets)}".lower()
    if any(word in hay for word in ["paperback", "hardcover", "book", "storybook", "author", "isbn"]):
        return "books"
    if any(word in hay for word in ["chocolate", "coffee", "tea", "honey", "snack", "food", "gift basket"]):
        return "food"
    if any(word in hay for word in ["serum", "cleanser", "mask", "oil", "cosmetic", "skincare", "beauty"]):
        return "skincare"
    if any(word in hay for word in ["pendant", "necklace", "earrings", "jade", "greenstone", "pounamu"]):
        return "jewelry"
    if any(word in hay for word in ["shirt", "beanie", "gloves", "wool", "merino", "clothing"]):
        return "clothing"
    return "artwork"


CATEGORY_META = {
    "artwork": {
        "label": "Artwork",
        "keywords": "new zealand artwork gift, kiwi wall art, auckland print, nz souvenir, local artwork",
    },
    "clothing": {
        "label": "Clothing",
        "keywords": "new zealand clothing gift, merino wool gift, kiwi clothing, swanndri, nz apparel",
    },
    "jewelry": {
        "label": "Jewelry",
        "keywords": "new zealand jewelry gift, jade necklace, pounamu pendant, greenstone earrings, kiwi keepsake",
    },
    "skincare": {
        "label": "Skincare",
        "keywords": "new zealand skincare gift, kiwi beauty, manuka honey skincare, natural self care, nz beauty gift",
    },
    "food": {
        "label": "Food",
        "keywords": "new zealand food gift, kiwi chocolate, nz treats, edible gift idea, nz snack gift",
    },
    "books": {
        "label": "Books",
        "keywords": "new zealand books, kiwi gift books, books about new zealand, nz nature book, aotearoa gift book",
    },
}


def generate_copy(title: str, category: str, bullets: list[str]) -> dict:
    joined = "; ".join(bullets[:3])
    label = CATEGORY_META[category]["label"]

    if category == "books":
        intro = (
            f"{title} is the kind of New Zealand book gift that feels thoughtful straight away. "
            "It suits curious readers, nature lovers, and anyone who likes gifts with a strong sense of place."
        )
        why = (
            "Books about Aotearoa work well because they travel easily, feel personal, and give people something they can keep returning to. "
            "This one fits readers who enjoy New Zealand wildlife, natural history, and stories that go beyond the usual souvenir angle."
        )
        story_title = "Why New Zealand books make such strong gifts"
        story_paragraphs = [
            f"If someone is searching for New Zealand books, Kiwi gift ideas, or thoughtful presents connected to Aotearoa, {title} lands in a very good place. It feels specific, intelligent, and easy to give. A good book is not just an object on a table. It becomes a conversation, a recommendation, and often the sort of gift that gets passed from one reader to the next.",
            "Books also solve a practical gift problem. They are easy to post, easy to wrap, and easy to choose when you want something more meaningful than a generic souvenir. In New Zealand gifting terms, a book works beautifully for birthdays, care packages, thank-you presents, travel gifts, and overseas friends who want a deeper connection to this part of the world.",
            f"For people searching terms like New Zealand nature books, books about New Zealand birds, Kiwi wildlife gifts, or educational New Zealand presents, this page naturally matches that intent. The best product pages do not force the keywords. They simply make it clear who the gift is for and why it belongs in the category. That is exactly what a book like this can do.",
        ]
    elif category == "food":
        intro = (
            f"{title} is an easy New Zealand food gift with strong crowd-pleaser energy. "
            "It suits hosts, coworkers, families, and anyone who likes classic Kiwi treats."
        )
        why = (
            "Food gifts work because they are easy to share and easy to enjoy. "
            "This one feels local, familiar, and genuinely useful for everyday gifting instead of sitting on a shelf unused."
        )
        story_title = "Why New Zealand food gifts work so well"
        story_paragraphs = [
            "Edible gifts tend to succeed because they feel low-pressure and generous at the same time. They are easy to bring to a dinner, easy to send as a thank-you, and easy to share around a workplace or family table.",
            f"If someone is searching for New Zealand food gifts, Kiwi treats, or edible gift ideas, {title} matches that intent naturally because it feels recognisable and easy to enjoy.",
            "That combination of familiarity and usefulness is what makes local food gifts so reliable. They fit birthdays, host gifts, coworker presents, care packages, and everyday little moments when a thoughtful treat is enough.",
        ]
    else:
        intro = (
            f"{title} is the kind of {label.lower()} gift that feels local without trying too hard. "
            "It fits the NZ Gift Finder style of useful, memorable, and easy-to-give picks."
        )
        why = (
            f"This works well as a New Zealand-inspired {label.lower()} gift because it has a clear sense of place and broad appeal. "
            "It feels considered rather than generic, which is usually what people want when they are buying something with Kiwi character."
        )
        story_title = f"Why this {label.lower()} gift works"
        story_paragraphs = [
            f"People searching for New Zealand {label.lower()} gifts are usually looking for something with local flavour and everyday usefulness. {title} fits that nicely because it feels specific, easy to understand, and simple to give.",
            "The strongest gift ideas tend to be the ones that make sense quickly. They are recognisable, they suit real people, and they do not feel like filler. That is where products like this can do well.",
            f"From a search-intent perspective, this page supports shoppers looking for Kiwi {label.lower()} gifts, New Zealand present ideas, and Aotearoa-inspired products that feel more thoughtful than generic online gift lists.",
        ]

    details = [item for item in bullets[:4] if item]
    if not details:
        if category == "books":
            details = [
                "A New Zealand book gift with strong wildlife and natural history appeal.",
                "Easy to wrap, post, and include in a thoughtful Kiwi care package.",
                "Suited to readers who enjoy birds, science, and Aotearoa-focused subjects.",
            ]
        elif joined:
            details = [joined]
        else:
            details = [
                f"A {label.lower()} pick with a clear New Zealand feel.",
                "Simple to gift and easy to understand at a glance.",
                "Chosen for local character, usefulness, and broad appeal.",
            ]

    meta_description = truncate(
        f"NZ Gift Finder pick: {intro} {why}", 160
    )

    return {
        "meta_description": meta_description,
        "meta_keywords": CATEGORY_META[category]["keywords"],
        "intro": intro,
        "why": why,
        "details": details,
        "story_title": story_title,
        "story_paragraphs": story_paragraphs,
        "card_sub": truncate(meta_description, 50),
    }


def render_product_page(*, title: str, category: str, images: list[str], amazon_link: str, meta_description: str, meta_keywords: str, intro: str, details: list[str], why: str, story_title: str, story_paragraphs: list[str]) -> str:
    category_label = CATEGORY_META[category]["label"]
    image1 = images[0] if images else "../images/pounamu_twist.png"
    thumbs = "\n".join(
        [
            f'''            <button class="thumb{' is-active' if i == 0 else ''}" type="button" data-src="{img}">\n                <img src="{img}" loading="lazy" />\n            </button>'''
            for i, img in enumerate(images[:6])
        ]
    )
    detail_html = "\n".join([f"              <li>{html.escape(item)}</li>" for item in details])
    story_html = "\n".join([f"            <p class=\"body\">{html.escape(p)}</p>" for p in story_paragraphs])

    return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />

    <title>{html.escape(title)} | NZ Gifts</title>

    <meta name="description" content="{html.escape(meta_description)}" />
    <meta name="keywords" content="{html.escape(meta_keywords)}" />
    <meta name="author" content="NZ Gifts" />

    <link rel="stylesheet" href="../style.css" />
  </head>
  <body>
    <div id="site-header"></div>

    <main class="wrap">
      <section class="hero">
        <div class="breadcrumb">
          <a href="../">Home</a> / <a href="./">{html.escape(category_label)}</a> /
          {html.escape(title)}
        </div>
        <h1 class="page-title">{html.escape(title)}</h1>
        <p class="intro">{html.escape(intro)}</p>
      </section>

      <section class="product-grid">
        <div class="gallery gallery-thumbs">
          <div class="main-image">
            <img
              id="mainProductImage"
              src="{html.escape(image1)}"
              alt="{html.escape(title)}"
              loading="lazy"
            />
          </div>

          <div class="thumb-row" aria-label="More views">
{thumbs}
          </div>

        <div class="details">
          <div class="kicker" style="margin-top:14px;">Product details</div>
          <ul class="body">
{detail_html}
          </ul>

          <div class="kicker">Why this one works</div>
          <p class="body">{html.escape(why)}</p>
          <a
            class="cta"
            href="{html.escape(amazon_link)}"
            target="_blank"
            rel="noopener"
          >
            View on Amazon
          </a>

          <div class="story-section" style="margin-top:22px;">
            <div class="kicker">{html.escape(story_title)}</div>
{story_html}

            <a
              class="cta"
              href="{html.escape(amazon_link)}"
              target="_blank"
              rel="noopener"
            >
              View on Amazon
            </a>
          </div>

          <p class="fineprint">
            Affiliate link. Price may change. We pick stuff we’d actually give.
          </p>
        </div>
      </section>
    </main>

    <div id="site-footer" class="footer-mount"></div>

    <script src="../app.js"></script>
  </body>
</html>
'''


def load_catalog(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_catalog(path: Path, items: list[dict]) -> None:
    path.write_text(json.dumps(items, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def upsert_catalog(category: str, entry: dict) -> None:
    path = ROOT / category / "products.json"
    items = load_catalog(path)
    items = [item for item in items if item.get("slug") != entry["slug"]]
    items.insert(0, entry)
    write_catalog(path, items)


def fetch_amazon_product(url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    raw_html = response.text
    title = extract_title(raw_html)
    images = extract_dynamic_images(raw_html)
    bullets = extract_bullets(raw_html)
    category = guess_category(title, bullets)
    return {
        "title": title,
        "images": images,
        "bullets": bullets,
        "category": category,
        "affiliate_url": normalize_affiliate_url(url),
        "source_url": url,
    }


def import_product(url: str, category: str | None = None) -> dict:
    product = fetch_amazon_product(url)
    final_category = category or product["category"]
    if final_category not in ALLOWED_CATEGORIES:
        raise ValueError(f"Unsupported category: {final_category}")
    title = product["title"]
    slug = slugify(title)
    copy = generate_copy(title, final_category, product["bullets"])
    out_dir = ROOT / final_category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.html"
    html_content = render_product_page(
        title=title,
        category=final_category,
        images=product["images"],
        amazon_link=product["affiliate_url"],
        meta_description=copy["meta_description"],
        meta_keywords=copy["meta_keywords"],
        intro=copy["intro"],
        details=copy["details"],
        why=copy["why"],
        story_title=copy["story_title"],
        story_paragraphs=copy["story_paragraphs"],
    )
    out_path.write_text(html_content, encoding="utf-8")
    upsert_catalog(
        final_category,
        {
            "slug": slug,
            "href": f"{slug}.html",
            "image": product["images"][0] if product["images"] else "",
            "alt": title,
            "title": title,
            "sub": copy["card_sub"],
        },
    )
    return {
        "title": title,
        "category": final_category,
        "slug": slug,
        "path": str(out_path.relative_to(ROOT)),
        "affiliate_url": product["affiliate_url"],
        "images": product["images"],
    }

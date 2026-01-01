import os, re
from datetime import datetime
from typing import Optional, List
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
    )
}

PRODUCTS_DIR = "products"
TEMPLATE_PATH = "product.html"
ASSET_PREFIX = "../"  # ALWAYS go up one level for css/images/index from /products/*.html
DEBUG = os.environ.get("DEBUG_SCRAPE") == "1"


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "product"


def fetch_html(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    if DEBUG:
        title = soup.title.get_text(" ", strip=True) if soup.title else "(no <title>)"
        product_title_count = len(soup.select("#productTitle"))
        landing_image_count = len(soup.select("#landingImage"))
        alt_images_count = len(soup.select("#altImages img[src]"))

        print(
            "[debug] status",
            r.status_code,
            "url",
            r.url,
            "len",
            len(r.text),
            "title",
            title,
            "productTitle nodes",
            product_title_count,
            "landingImage nodes",
            landing_image_count,
            "altImages imgs",
            alt_images_count,
        )

        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("[debug] wrote raw HTML to debug.html")

    return soup


def pick_main_image(soup: BeautifulSoup) -> Optional[str]:
    # 1) most reliable static source
    og = soup.select_one('meta[property="og:image"][content]')
    if og and og.get("content"):
        return og["content"].strip()

    # 2) your requested target (only sometimes present in raw HTML)
    img = soup.select_one("img.fullscreen[src]")
    if img and img.get("src"):
        return img["src"].strip()

    # 3) common Amazon main image patterns
    landing = soup.select_one("#landingImage")
    if landing:
        hires = landing.get("data-old-hires")
        if hires and hires.strip():
            return hires.strip()
        src = landing.get("src")
        if src and src.strip():
            return src.strip()

    wrapper = soup.select_one("#imgTagWrapperId img[src]")
    if wrapper and wrapper.get("src"):
        return wrapper["src"].strip()

    return None


def fetch_product(url: str) -> dict:
    soup = fetch_html(url)

    title_el = soup.select_one("#productTitle")
    title = title_el.get_text(" ", strip=True) if title_el else "NZ Gift"

    images: List[str] = []
    main_img = pick_main_image(soup)
    if main_img:
        images.append(main_img)

    # fallback to thumbnails if needed
    if not images:
        for img in soup.select("#altImages img[src]"):
            src = (img.get("src") or "").strip()
            if "m.media-amazon.com" in src:
                images.append(src)
        images = images[:6]

    return {"title": title, "images": images, "url": url}


def build_image_html(urls: List[str]) -> str:
    # If Amazon image scraping fails, fall back to your local logo
    if not urls:
        return f'<img src="{ASSET_PREFIX}images/pounamu_twist.png" alt="Product image" />'
    return "\n".join(
        f'<img src="{u}" alt="Product photo" loading="lazy" />'
        for u in urls
        if u
    )


def fix_asset_paths_in_template(tpl: str) -> str:
    """
    Your template was written as if it's in root.
    But output files are ALWAYS in /products/, so we rewrite common paths.
    """

    # stylesheet
    tpl = tpl.replace('href="style.css"', f'href="{ASSET_PREFIX}style.css"')
    tpl = tpl.replace("href='style.css'", f"href='{ASSET_PREFIX}style.css'")

    # index link (brand + any other links)
    tpl = tpl.replace('href="index.html"', f'href="{ASSET_PREFIX}index.html"')
    tpl = tpl.replace("href='index.html'", f"href='{ASSET_PREFIX}index.html'")

    # logo image path (and any other root images/)
    tpl = tpl.replace('src="images/', f'src="{ASSET_PREFIX}images/')
    tpl = tpl.replace("src='images/", f"src='{ASSET_PREFIX}images/")

    # any css url(images/...) inside <style> blocks (rare, but safe)
    tpl = tpl.replace("url(images/", f"url({ASSET_PREFIX}images/")

    return tpl


def render(template_path: str, out_path: str, data: dict):
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    tpl = fix_asset_paths_in_template(tpl)

    short_blurb = (
        "Simple, iconic, and not try-hard. Works for birthdays, visitors, "
        "and that one person who is impossible to buy for."
    )

    html = (
        tpl.replace("{{PAGE_TITLE}}", f"{data['title']} | NZ Gifts")
          .replace("{{PRODUCT_TITLE}}", data["title"])
          .replace("{{AMAZON_URL}}", data["url"])
          .replace("{{IMAGE_HTML}}", build_image_html(data["images"]))
          .replace("{{SHORT_BLURB}}", short_blurb)
          .replace("{{YEAR}}", str(datetime.now().year))
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    url = input("Amazon product url: ").strip()
    data = fetch_product(url)
    slug = slugify(data["title"])
    out_file = os.path.join(PRODUCTS_DIR, f"{slug}.html")
    render(TEMPLATE_PATH, out_file, data)
    print(f"wrote {out_file}")


if __name__ == "__main__":
    main()

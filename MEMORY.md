# NZ Gift Finder Memory

This file is a working memory for how to create and edit pages on the NZ Gift Finder site.

## Core page style

- Tone should feel human, confident, Kiwi-aware, and natural.
- Avoid generic corporate fluff and avoid touristy, cheesy phrasing.
- Copy should feel thoughtful, grounded, and useful rather than overhyped.
- Prefer language that sounds like a real recommendation from someone who understands New Zealand gifting culture.

## SEO and AI-SEO style

- Use organic search-intent phrasing throughout the page.
- Sprinkle in realistic phrases people might search for, such as:
  - New Zealand gift ideas
  - Kiwi gifts
  - gifts from NZ
  - New Zealand books / food gifts / skincare gifts / jewelry gifts / clothing gifts / artwork gifts
  - gifts for coworkers, hosts, family, overseas friends, birthdays, care packages, housewarming gifts
- Keep keyword use natural. Do not stuff.
- Write copy so AI summaries can easily understand:
  - what the item is
  - who it is for
  - why it works as a New Zealand gift
  - what search intent it satisfies

## Product page structure

Preferred structure for product pages:

1. Strong title
2. Natural intro paragraph
3. Product details bullets
4. "Why this one works" section
5. First Amazon button
6. Long story/search-intent section below the first Amazon button
7. Repeat the same Amazon button again at the end of the story section
8. Affiliate disclaimer at the bottom

## Story section rules

- Story sections should be long, warm, and specific.
- They can include invented but believable stories and gifting scenarios.
- They should connect the product to real New Zealand usage and gifting culture.
- They should mention realistic recipients and occasions.
- They should reinforce likely search intent in a natural way.

Examples of useful angles:
- coworkers sharing food gifts
- hosts and housewarming gifts
- family gifts
- gifts for people overseas who miss New Zealand
- thoughtful gifts that are easy to post, wrap, or carry

## Amazon button rules

- If a second Amazon button is added lower on the page, it must use the exact same affiliate URL as the original button on that page.
- Never replace a page-specific affiliate link with some other Amazon link.
- Preserve the supplied affiliate URL exactly unless there is a very deliberate normalization step that keeps the affiliate parameters intact.

## Image rules

- Use images from the actual Amazon product listing, not local category images, logos, or placeholders.
- The main image and thumbnails should reflect the listing the page links to.
- Update the category `products.json` card image to use the product's Amazon image too.
- If the Amazon listing images cannot be captured reliably, stop and fix that first instead of publishing the page with a fake or generic image.
- Do not use multiple size variants of the same Amazon image on one page.
- Each thumbnail should be a genuinely different listing image with a different physical/media ID, not the same image resized.
- When extracting from Amazon, deduplicate by the underlying image/media identity first, then choose one preferred size per unique image.

## Category rules

Current categories include:
- artwork
- clothing
- jewelry
- skincare
- food
- books

Books should go in the Books category, not Artwork.

## Books category guidance

- Books are a valid and preferred category when the product is clearly a book.
- Books should be framed as thoughtful, easy-to-post New Zealand gifts.
- Good angles include wildlife, culture, nature, children’s reading, education, and meaningful keepsakes.

## Step-by-step workflow for creating a new product page

1. **Confirm the product is actually on Amazon US.**
   - Use a direct Amazon.com link, not another locale.
   - Make sure the product is clearly New Zealand-related and fits the site.

2. **Check availability before doing any page work.**
   - Confirm the listing is purchasable or at least not marked "Currently unavailable."
   - If it is unavailable, do not publish the page unless explicitly told to keep a placeholder watch page.
   - If it is unavailable but still worth tracking, note it in memory as a watch candidate.

3. **Capture the real Amazon listing assets.**
   - Pull the product title from the listing.
   - Pull the Amazon product images from the listing.
   - Pull a few useful product details / bullets.
   - Do not substitute local placeholder images.

4. **Choose the correct category.**
   - food, books, skincare, jewelry, clothing, or artwork.
   - If in doubt, choose the category that best matches how a human would shop for it on this site.

5. **Write the page in the NZ Gift Finder voice.**
   - Keep the tone curated, natural, and Kiwi-aware.
   - Make it sound like a real recommendation, not an SEO content farm.
   - Use natural search-intent phrasing without stuffing.

6. **Follow the standard product-page structure.**
   - Title
   - Intro
   - Product details bullets
   - Why this one works
   - Amazon button
   - Long story/search-intent section
   - Same Amazon button again
   - Affiliate disclaimer

7. **Keep the Amazon URL exact.**
   - Reuse the same product-specific affiliate URL for both CTA buttons.
   - Do not silently swap in another Amazon link.

8. **Update the category catalog.**
   - Add the product to the relevant category `products.json`.
   - Use the real Amazon product image in the card entry.
   - Write a short, human subline that fits the site.

9. **Sanity-check the finished page.**
   - Confirm the breadcrumb/category is correct.
   - Confirm the images are the Amazon listing images.
   - Confirm the product is still available.
   - Confirm both CTA buttons point to the same URL.
   - Confirm the copy reads naturally.
   - If the Amazon listing only exposes one genuinely unique image, use one image only rather than padding the gallery with duplicates or resized variants.

10. **Commit after edits.**
   - Commit cleanly once the page and catalog are correct.
   - Push when the user asks, or when the request explicitly includes pushing.

## Editing preferences

- Prefer tiny, clean improvements over big redesigns.
- Keep SEO improvements light-touch and organic.
- Preserve page-specific affiliate links.
- When moving a product between categories, update:
  - the file location
  - breadcrumb/category text in the page
  - the old category products.json
  - the new category products.json

## Workflow preferences

- Commit changes after edits.
- Push when the user asks, or when the request explicitly includes pushing.
- For new imports, the intended workflow is: user sends Amazon link, availability is checked, listing images/details are captured, page gets created, category catalog updated, then commit/push.

## Current watch list

- Kiva Certified UMF 15+ Raw Manuka Honey with Gift Box (`https://www.amazon.com/Kiva-Certified-Manuka-Honey-GIFT/dp/B07HYFLM7W`) was marked "Currently unavailable" when reviewed on 2026-03-12 NZ time. If it comes back, it is a good candidate for a future NZ Gift Finder food page.

from __future__ import annotations

import argparse
import json

from product_pipeline import ALLOWED_CATEGORIES, import_product


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an Amazon product into NZ Gift Finder.")
    parser.add_argument("url", help="Amazon product URL")
    parser.add_argument("--category", choices=ALLOWED_CATEGORIES, help="Optional category override")
    args = parser.parse_args()

    result = import_product(args.url, category=args.category)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

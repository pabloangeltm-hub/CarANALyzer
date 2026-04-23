"""
Scrape a single website and return structured text content.

Usage:
    python tools/scrape_website.py --url https://example.com
    python tools/scrape_website.py --url https://example.com --output .tmp/page.txt

    Or as a module:
    from tools.scrape_website import scrape
    content = scrape("https://example.com")
"""
import argparse
import os
import sys
import requests
from bs4 import BeautifulSoup


def scrape(url: str, timeout: int = 15) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else ""
    body_text = soup.get_text(separator="\n", strip=True)

    lines = [line for line in body_text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    return {
        "url": url,
        "title": title,
        "text": clean_text,
        "status_code": response.status_code,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a single website")
    parser.add_argument("--url", required=True, help="URL to scrape")
    parser.add_argument("--output", help="Save output to this file path")
    args = parser.parse_args()

    result = scrape(args.url)
    print(f"[OK] Scraped: {result['title']} ({result['status_code']})")
    print(f"     {len(result['text'])} characters extracted")

    if args.output:
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"URL: {result['url']}\n")
            f.write(f"Title: {result['title']}\n")
            f.write("---\n")
            f.write(result["text"])
        print(f"[OK] Saved to {args.output}")
    else:
        print("\n--- Content ---")
        print(result["text"][:2000])
        if len(result["text"]) > 2000:
            print(f"\n... ({len(result['text']) - 2000} more characters)")

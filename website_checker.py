"""Verify if businesses have working websites."""

import concurrent.futures
import requests
import sys
from rich.console import Console

from sources.base import Business
import config

console = Console(force_terminal=True)


def check_websites(businesses: list[Business]) -> list[Business]:
    """
    Check each business's website to verify if it's live.
    Updates the has_website field based on actual HTTP checks.

    Args:
        businesses: List of Business objects to check

    Returns:
        Updated list with has_website field set accurately
    """
    # Only check businesses that have a website URL listed
    to_check = [b for b in businesses if b.website]
    no_website = [b for b in businesses if not b.website]

    if not to_check:
        console.print("[cyan]Website Check:[/] No websites to verify")
        return businesses

    console.print(f"[cyan]Website Check:[/] Verifying {len(to_check)} websites...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_biz = {
            executor.submit(_is_website_live, biz.website): biz
            for biz in to_check
        }

        for future in concurrent.futures.as_completed(future_to_biz):
            biz = future_to_biz[future]
            try:
                is_live = future.result()
                biz.has_website = is_live
                if not is_live:
                    print(f"  Dead site: {biz.name} -> {biz.website}")
            except Exception:
                biz.has_website = False

    live_count = sum(1 for b in to_check if b.has_website)
    dead_count = len(to_check) - live_count

    print(f"  Website Check: {live_count} live, {dead_count} dead/unreachable")
    print(f"  Total without website: {len(no_website) + dead_count} businesses")

    return businesses


def _is_website_live(url: str) -> bool:
    """Check if a URL is reachable and returns a valid response."""
    if not url:
        return False

    # Ensure URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Try HEAD first, fall back to GET (many sites block HEAD)
    for method in (requests.head, requests.get):
        try:
            resp = method(
                url,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=True,
                headers=headers,
                stream=True,  # don't download full body for GET
            )
            if resp.status_code < 400:
                resp.close()
                return True
            resp.close()
        except requests.exceptions.RequestException:
            pass

    # Try HTTP fallback
    fallback_url = url.replace("https://", "http://")
    if fallback_url != url:
        try:
            resp = requests.get(
                fallback_url,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=True,
                headers=headers,
                stream=True,
            )
            if resp.status_code < 400:
                resp.close()
                return True
            resp.close()
        except requests.exceptions.RequestException:
            pass

    return False

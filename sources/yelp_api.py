"""Yelp Fusion API source (free tier: 500 requests/day)."""

import requests
from rich.console import Console

from sources.base import Business
import config

console = Console()

BASE_URL = "https://api.yelp.com/v3/businesses/search"


def search(location: str, category: str, limit: int = 20) -> list[Business]:
    """
    Search Yelp for businesses.

    Args:
        location: City or area (e.g., "Mumbai, India")
        category: Business type (e.g., "restaurants")
        limit: Max results (Yelp max is 50 per request)

    Returns:
        List of Business objects
    """
    if not config.YELP_API_KEY:
        console.print("[yellow]Yelp:[/] Skipped (no API key set in .env)")
        return []

    console.print(f"[cyan]Yelp:[/] Searching '{category}' in '{location}'...")
    businesses = []

    headers = {"Authorization": f"Bearer {config.YELP_API_KEY}"}
    params = {
        "location": location,
        "term": category,
        "limit": min(limit, 50),
        "sort_by": "distance",
    }

    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        for biz in data.get("businesses", []):
            loc = biz.get("location", {})
            address_parts = [
                loc.get("address1", ""),
                loc.get("city", ""),
                loc.get("state", ""),
                loc.get("zip_code", ""),
            ]
            address = ", ".join(p for p in address_parts if p)

            categories = ", ".join(c.get("title", "") for c in biz.get("categories", []))

            website = biz.get("url", "")  # Yelp page URL, not business website
            # Yelp API doesn't return business websites directly
            # We'll check this in the website checker module

            business = Business(
                name=biz.get("name", ""),
                address=address,
                phone=biz.get("display_phone", ""),
                website="",  # Yelp doesn't provide business websites via API
                rating=biz.get("rating", 0.0),
                review_count=biz.get("review_count", 0),
                category=categories,
                latitude=biz.get("coordinates", {}).get("latitude", 0.0),
                longitude=biz.get("coordinates", {}).get("longitude", 0.0),
                source="yelp",
                has_website=False,  # Unknown, will verify later
            )
            businesses.append(business)
            console.print(f"  [green]Found:[/] {business.name}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            console.print("[red]Yelp:[/] Invalid API key. Check your .env file.")
        else:
            console.print(f"[red]Yelp error:[/] {e}")
    except Exception as e:
        console.print(f"[red]Yelp error:[/] {e}")

    console.print(f"[cyan]Yelp:[/] Found {len(businesses)} businesses")
    return businesses

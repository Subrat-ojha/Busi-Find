"""Foursquare Places API source (free tier available)."""

import requests
from rich.console import Console

from sources.base import Business
import config

console = Console()

BASE_URL = "https://api.foursquare.com/v3/places/search"


def search(location: str, category: str, limit: int = 20) -> list[Business]:
    """
    Search Foursquare for businesses.

    Args:
        location: City or area (e.g., "Mumbai, India")
        category: Business type (e.g., "restaurants")
        limit: Max results (Foursquare max is 50 per request)

    Returns:
        List of Business objects
    """
    if not config.FOURSQUARE_API_KEY:
        console.print("[yellow]Foursquare:[/] Skipped (no API key set in .env)")
        return []

    console.print(f"[cyan]Foursquare:[/] Searching '{category}' in '{location}'...")
    businesses = []

    headers = {
        "Authorization": config.FOURSQUARE_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "query": category,
        "near": location,
        "limit": min(limit, 50),
        "fields": "name,location,tel,website,rating,categories,geocodes",
    }

    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        for place in data.get("results", []):
            loc = place.get("location", {})
            address = loc.get("formatted_address", loc.get("address", ""))

            categories = ", ".join(
                c.get("name", "") for c in place.get("categories", [])
            )

            geocodes = place.get("geocodes", {}).get("main", {})
            website = place.get("website", "")

            business = Business(
                name=place.get("name", ""),
                address=address,
                phone=place.get("tel", ""),
                website=website,
                rating=place.get("rating", 0.0) / 2,  # Foursquare uses 0-10, normalize to 0-5
                category=categories,
                latitude=geocodes.get("latitude", 0.0),
                longitude=geocodes.get("longitude", 0.0),
                source="foursquare",
                has_website=bool(website),
            )
            businesses.append(business)
            console.print(f"  [green]Found:[/] {business.name}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            console.print("[red]Foursquare:[/] Invalid API key. Check your .env file.")
        else:
            console.print(f"[red]Foursquare error:[/] {e}")
    except Exception as e:
        console.print(f"[red]Foursquare error:[/] {e}")

    console.print(f"[cyan]Foursquare:[/] Found {len(businesses)} businesses")
    return businesses

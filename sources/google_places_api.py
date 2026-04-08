"""Google Places API source (free $200/month credit)."""

import requests
from rich.console import Console

from sources.base import Business
import config

console = Console()

TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def search(location: str, category: str, limit: int = 20) -> list[Business]:
    """
    Search Google Places API for businesses.

    Args:
        location: City or area (e.g., "Mumbai, India")
        category: Business type (e.g., "restaurants")
        limit: Max results to collect

    Returns:
        List of Business objects
    """
    if not config.GOOGLE_API_KEY:
        console.print("[yellow]Google Places API:[/] Skipped (no API key set in .env)")
        return []

    query = f"{category} in {location}"
    console.print(f"[cyan]Google Places API:[/] Searching '{query}'...")
    businesses = []

    params = {
        "query": query,
        "key": config.GOOGLE_API_KEY,
    }

    try:
        collected = 0
        next_page_token = None

        while collected < limit:
            if next_page_token:
                params["pagetoken"] = next_page_token

            resp = requests.get(TEXTSEARCH_URL, params=params, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "OK":
                console.print(f"[red]Google Places API:[/] {data.get('status')} - {data.get('error_message', '')}")
                break

            for place in data.get("results", []):
                if collected >= limit:
                    break

                # Get details for website and phone
                details = _get_details(place.get("place_id", ""))

                types = place.get("types", [])
                category_str = ", ".join(t.replace("_", " ") for t in types[:3])

                website = details.get("website", "")
                business = Business(
                    name=place.get("name", ""),
                    address=place.get("formatted_address", ""),
                    phone=details.get("formatted_phone_number", ""),
                    website=website,
                    rating=place.get("rating", 0.0),
                    review_count=place.get("user_ratings_total", 0),
                    category=category_str,
                    latitude=place.get("geometry", {}).get("location", {}).get("lat", 0.0),
                    longitude=place.get("geometry", {}).get("location", {}).get("lng", 0.0),
                    source="google_places_api",
                    has_website=bool(website),
                )
                businesses.append(business)
                collected += 1
                console.print(f"  [green]Found:[/] {business.name}")

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

    except Exception as e:
        console.print(f"[red]Google Places API error:[/] {e}")

    console.print(f"[cyan]Google Places API:[/] Found {len(businesses)} businesses")
    return businesses


def _get_details(place_id: str) -> dict:
    """Fetch place details (website, phone) for a given place_id."""
    if not place_id:
        return {}

    params = {
        "place_id": place_id,
        "fields": "website,formatted_phone_number",
        "key": config.GOOGLE_API_KEY,
    }

    try:
        resp = requests.get(DETAILS_URL, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {})
    except Exception:
        return {}

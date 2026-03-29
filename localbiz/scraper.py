"""
Business Discovery Agent
Scrapes Google Maps via SerpAPI to find local businesses without websites.
"""
import os
import time
from urllib.parse import urlparse

import requests
from serpapi import GoogleSearch


def discover_leads(category: str, location: str, limit: int = 100) -> list[dict]:
    """
    Search Google Maps for businesses in a category/location,
    returning only those without a live website.
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY environment variable not set. See .env.example.")

    leads = []
    seen = set()
    start = 0

    print(f"  Searching: '{category}' in '{location}'")

    while len(leads) < limit:
        params = {
            "engine": "google_maps",
            "q": f"{category} {location}",
            "type": "search",
            "api_key": api_key,
            "start": start,
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        places = results.get("local_results", [])

        if not places:
            break

        for place in places:
            if len(leads) >= limit:
                break

            place_id = place.get("place_id", "")
            if place_id in seen:
                continue
            seen.add(place_id)

            website = place.get("website", "")
            if website and is_live_website(website):
                continue  # Already has a working site

            lead = {
                "name": place.get("title", "").strip(),
                "address": place.get("address", "").strip(),
                "phone": place.get("phone", "").strip(),
                "existing_website": website,
                "rating": place.get("rating", 0),
                "reviews": place.get("reviews", 0),
                "category": category,
                "place_id": place_id,
                "hours": _extract_hours(place),
                "thumbnail": place.get("thumbnail", ""),
            }

            if lead["name"]:
                leads.append(lead)
                print(f"  + {lead['name']} ({lead['address']})")

        start += 20
        if len(places) < 20:
            break  # No more pages

        time.sleep(0.5)  # Polite rate limit

    return leads


def is_live_website(url: str) -> bool:
    """Return True if the URL responds with a non-error HTTP status."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
        resp = requests.head(url, timeout=6, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
        return resp.status_code < 400
    except Exception:
        return False


def _extract_hours(place: dict) -> str:
    """Flatten opening hours into a readable string."""
    hours = place.get("hours", "")
    if isinstance(hours, dict):
        return " | ".join(f"{day}: {times}" for day, times in hours.items())
    if isinstance(hours, list):
        return " | ".join(hours)
    return str(hours).strip() if hours else ""

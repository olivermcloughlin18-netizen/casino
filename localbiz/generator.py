"""
Website Generation Agent
Generates a tailored 1-page HTML site for each lead.
Uses OpenAI for copy; falls back to template placeholders in test mode.
"""
import json
import os
import re
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "templates" / "business.html"

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from openai import OpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            _client = OpenAI(api_key=api_key)
        except Exception as e:
            raise RuntimeError(f"OpenAI client unavailable: {e}")
    return _client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_website(lead: dict, output_dir: Path, test_mode: bool = False) -> Path:
    """Generate and save a website for the given lead. Returns the file path."""
    if test_mode:
        content = _mock_content(lead)
    else:
        content = _generate_content_ai(lead)

    html = _render_template(lead, content)

    slug = _slugify(lead["name"])
    site_path = output_dir / slug / "index.html"
    site_path.parent.mkdir(parents=True, exist_ok=True)
    site_path.write_text(html, encoding="utf-8")
    return site_path


# ---------------------------------------------------------------------------
# Content generation
# ---------------------------------------------------------------------------

def _generate_content_ai(lead: dict) -> dict:
    """Call OpenAI to generate tailored website copy."""
    prompt = f"""Generate website copy for a local Melbourne small business.

Business details:
- Name: {lead['name']}
- Category: {lead['category']}
- Address: {lead.get('address', 'Melbourne, VIC')}
- Phone: {lead.get('phone', 'not provided')}
- Rating: {lead.get('rating', 'N/A')} ({lead.get('reviews', 0)} reviews on Google)

Return a JSON object with exactly these fields:
- tagline: punchy tagline, max 10 words
- hero_description: 1-2 sentence compelling intro, mention the suburb if known
- services: array of 3-5 objects, each with "name" (string) and "description" (1 sentence string)
- about: 2-3 sentences telling the business story, warm and local
- cta_text: call-to-action button text (e.g. "Book Now", "Call Us Today", "Get a Quote")
- seo_keywords: array of 4-6 local SEO phrases including suburb and "near me" variants

Return only valid JSON. No markdown fences."""

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def _mock_content(lead: dict) -> dict:
    """Return deterministic placeholder content for test mode (no API needed)."""
    name = lead["name"]
    category = lead["category"].title()
    suburb = _extract_suburb(lead.get("address", "Melbourne"))

    return {
        "tagline": f"Your trusted local {category} in {suburb}",
        "hero_description": (
            f"Welcome to {name} — proudly serving the {suburb} community "
            f"with quality {category.lower()} services you can count on."
        ),
        "services": [
            {"name": f"{category} Service", "description": f"Premium {category.lower()} service tailored to your needs."},
            {"name": "Consultation", "description": "Book a free consultation and we'll walk you through your options."},
            {"name": "Express Appointments", "description": "Short on time? Ask about our express same-day bookings."},
        ],
        "about": (
            f"{name} has been a cornerstone of the {suburb} community for years. "
            f"We take pride in delivering honest, high-quality {category.lower()} services "
            f"with a personal touch that the big chains simply can't match."
        ),
        "cta_text": "Contact Us Today",
        "seo_keywords": [
            f"{category.lower()} {suburb}",
            f"best {category.lower()} near me",
            f"{suburb} local {category.lower()}",
            f"{category.lower()} Melbourne",
        ],
    }


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def _render_template(lead: dict, content: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    suburb = _extract_suburb(lead.get("address", "Melbourne"))
    keywords = ", ".join(content.get("seo_keywords", []))

    replacements = {
        "{{BUSINESS_NAME}}":  lead.get("name", ""),
        "{{TAGLINE}}":        content.get("tagline", ""),
        "{{HERO_DESC}}":      content.get("hero_description", ""),
        "{{PHONE}}":          lead.get("phone", ""),
        "{{ADDRESS}}":        lead.get("address", ""),
        "{{SUBURB}}":         suburb,
        "{{CATEGORY}}":       lead.get("category", "").title(),
        "{{ABOUT}}":          content.get("about", ""),
        "{{CTA_TEXT}}":       content.get("cta_text", "Contact Us"),
        "{{SEO_KEYWORDS}}":   keywords,
        "{{SERVICES_HTML}}":  _render_services(content.get("services", [])),
        "{{HOURS_HTML}}":     _render_hours(lead.get("hours", "")),
        "{{MAPS_EMBED}}":     _render_maps_embed(lead.get("address", "")),
        "{{RATING}}":         str(lead.get("rating", "")),
        "{{REVIEWS}}":        str(lead.get("reviews", "")),
    }

    for key, val in replacements.items():
        template = template.replace(key, val)

    return template


def _render_services(services: list) -> str:
    if not services:
        return ""
    icons = ["✂️", "☕", "🔧", "⭐", "🏆", "🎯", "💡", "🛠️"]
    cards = []
    for i, svc in enumerate(services):
        icon = icons[i % len(icons)]
        cards.append(
            f'<div class="service-card">'
            f'<div class="service-icon">{icon}</div>'
            f'<h3>{svc.get("name", "")}</h3>'
            f'<p>{svc.get("description", "")}</p>'
            f'</div>'
        )
    return "\n".join(cards)


def _render_hours(hours_str: str) -> str:
    if not hours_str:
        return "<p>Call us for current opening hours.</p>"
    parts = [p.strip() for p in hours_str.split("|") if p.strip()]
    rows = []
    for part in parts:
        if ":" in part:
            day, _, time = part.partition(":")
            rows.append(f"<tr><td>{day.strip()}</td><td>{time.strip()}</td></tr>")
    if rows:
        return f"<table>{''.join(rows)}</table>"
    return f"<p>{hours_str}</p>"


def _render_maps_embed(address: str) -> str:
    if not address:
        return ""
    encoded = address.replace(" ", "+").replace(",", "%2C")
    return (
        f'<iframe '
        f'src="https://maps.google.com/maps?q={encoded}&output=embed" '
        f'width="100%" height="300" frameborder="0" '
        f'style="border:0;border-radius:8px;" '
        f'allowfullscreen="" loading="lazy"></iframe>'
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_suburb(address: str) -> str:
    if not address:
        return "Melbourne"
    parts = [p.strip() for p in address.split(",")]
    # Address format: "123 Smith St, Fitzroy VIC 3065, Australia"
    # Suburb is usually the first non-numeric-leading part after the street
    for part in parts:
        part_clean = re.sub(r"\d", "", part).strip()
        if part_clean and "Australia" not in part and "VIC" not in part:
            return part_clean.split()[0] if part_clean else "Melbourne"
    return parts[0] if parts else "Melbourne"


def _slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    return name or "business"

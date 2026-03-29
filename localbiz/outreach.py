"""
Outreach message generator.
Produces personalised SMS / email copy for each qualified lead.
In test mode this module is imported but no messages are sent.
"""
from pathlib import Path


def generate_outreach(lead: dict) -> dict:
    """Return a dict with 'sms' and 'email' message strings for the lead."""
    name     = lead.get("name", "your business")
    phone    = lead.get("phone", "")
    suburb   = _suburb(lead.get("address", ""))
    site_url = _site_url(lead.get("site_path", ""))

    sms   = _sms_template(name, suburb, site_url)
    email = _email_template(name, suburb, site_url, phone)

    return {"sms": sms, "email": email}


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def _sms_template(name: str, suburb: str, site_url: str) -> str:
    return (
        f"Hi! I noticed {name} in {suburb} doesn't have a website, "
        f"so I built one for you as a free preview:\n\n"
        f"{site_url}\n\n"
        f"It's yours to keep — just reply to this message if you'd like it live. "
        f"No obligation."
    )


def _email_template(name: str, suburb: str, site_url: str, phone: str) -> str:
    return f"""Subject: I made a free website for {name}

Hi there,

I'm a local web developer based in Melbourne, and I noticed {name} in {suburb}
doesn't have a website yet.

So I built one for you — no strings attached:

  👉 {site_url}

It includes:
  ✓ Your services & contact details
  ✓ Google Maps location embed
  ✓ Mobile-friendly, fast-loading design
  ✓ Local SEO keywords for {suburb}

If you'd like it live with your own domain (e.g. {_domain_hint(name)}),
I can set it up for a one-off fee of $199, which includes 12 months of hosting.

No commitment needed — I just wanted to show you what's possible for your business.

Reply to this email or call/text me anytime.

Cheers,
Oliver
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _suburb(address: str) -> str:
    if not address:
        return "Melbourne"
    parts = [p.strip() for p in address.split(",")]
    return parts[1] if len(parts) > 1 else parts[0]


def _site_url(site_path: str) -> str:
    """Convert a local file path to a placeholder URL for the message."""
    if not site_path:
        return "[preview link]"
    slug = Path(site_path).parent.name
    return f"https://preview.localbiz.com.au/{slug}"


def _domain_hint(name: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]", "", name.lower().replace(" ", ""))
    return f"www.{slug[:20]}.com.au"

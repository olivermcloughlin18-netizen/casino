#!/usr/bin/env python3
"""
LocalBiz Web Agent — Melbourne
Finds local businesses without websites, generates tailored sites, prepares outreach.

Usage
-----
  # Test mode (no API keys needed — uses mock data):
  python main.py --test

  # Real run (requires SERPAPI_KEY + OPENAI_API_KEY in environment):
  python main.py --category barber --limit 50

  # Full options:
  python main.py --category cafe --location "Fitzroy, Melbourne" \\
                 --limit 100 --min-score 60 --output-dir output --test
"""
import argparse
import csv
import os
import sys
from pathlib import Path

# Load .env automatically if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from qualifier import qualify_leads
from generator import generate_website
from outreach import generate_outreach


# ---------------------------------------------------------------------------
# Mock data for --test mode
# ---------------------------------------------------------------------------

MOCK_LEADS = [
    {
        "name": "Tony's Barber Shop",
        "address": "142 Brunswick St, Fitzroy VIC 3065, Australia",
        "phone": "03 9417 1234",
        "existing_website": "",
        "rating": 4.7,
        "reviews": 63,
        "category": "barber",
        "place_id": "mock_001",
        "hours": "Mon-Fri: 9am-6pm | Sat: 8am-5pm | Sun: Closed",
        "thumbnail": "",
    },
    {
        "name": "Sunrise Cafe",
        "address": "8 Chapel St, Prahran VIC 3181, Australia",
        "phone": "03 9510 5678",
        "existing_website": "",
        "rating": 4.5,
        "reviews": 112,
        "category": "cafe",
        "place_id": "mock_002",
        "hours": "Mon-Sun: 7am-3pm",
        "thumbnail": "",
    },
    {
        "name": "Pete's Auto Repair",
        "address": "77 Dynon Rd, West Melbourne VIC 3003, Australia",
        "phone": "0412 987 654",
        "existing_website": "",
        "rating": 4.8,
        "reviews": 38,
        "category": "mechanic",
        "place_id": "mock_003",
        "hours": "Mon-Fri: 8am-5:30pm | Sat: 8am-1pm",
        "thumbnail": "",
    },
    {
        "name": "Golden Dragon Takeaway",
        "address": "23 Swanston St, Melbourne VIC 3000, Australia",
        "phone": "03 9663 9999",
        "existing_website": "",
        "rating": 4.2,
        "reviews": 88,
        "category": "takeaway",
        "place_id": "mock_004",
        "hours": "Mon-Sun: 11am-10pm",
        "thumbnail": "",
    },
    {
        "name": "Bloom Florist",
        "address": "5 High St, Northcote VIC 3070, Australia",
        "phone": "03 9481 2200",
        "existing_website": "",
        "rating": 4.9,
        "reviews": 47,
        "category": "florist",
        "place_id": "mock_005",
        "hours": "Mon-Sat: 8am-6pm | Sun: 9am-3pm",
        "thumbnail": "",
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # ── 1. Discover leads ──────────────────────────────────────────────────
    if args.test:
        print("\n[TEST MODE] Using mock lead data — no API calls to SerpAPI.\n")
        raw_leads = [l for l in MOCK_LEADS if l["category"] == args.category] or MOCK_LEADS
        print(f"[1/3] Loaded {len(raw_leads)} mock leads for '{args.category}'")
    else:
        from scraper import discover_leads
        print(f"\n[1/3] Discovering '{args.category}' businesses in '{args.location}'...")
        raw_leads = discover_leads(args.category, args.location, args.limit)
        print(f"      Found {len(raw_leads)} businesses without websites")

    # ── 2. Qualify ─────────────────────────────────────────────────────────
    print(f"\n[2/3] Qualifying leads (min score: {args.min_score})...")
    qualified = qualify_leads(raw_leads, min_score=args.min_score)
    print(f"      {len(qualified)} leads qualified\n")

    if not qualified:
        print("No leads passed qualification. Lower --min-score or check your inputs.")
        sys.exit(0)

    # ── 3. Generate websites ───────────────────────────────────────────────
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.test:
        print(f"[3/3] Generating websites (test mode — no OpenAI calls)...\n")
    else:
        print(f"[3/3] Generating websites (using OpenAI)...\n")

    for lead in qualified:
        site_path = generate_website(lead, output_dir, test_mode=args.test)
        lead["site_path"] = str(site_path)
        msgs = generate_outreach(lead)
        lead["outreach_sms"]   = msgs["sms"]
        lead["outreach_email"] = msgs["email"]
        print(f"  ✓  {lead['name']:<35} score={lead['score']:>3}  →  {site_path}")

    # ── Save leads CSV ─────────────────────────────────────────────────────
    csv_path = Path(args.leads_file)
    _save_csv(qualified, csv_path)

    print(f"\n{'─'*60}")
    print(f"Done!  {len(qualified)} sites generated in '{output_dir}/'")
    print(f"Leads saved to '{csv_path}'")
    if args.test:
        print("\nRun without --test to use real Google Maps data + AI copy.")
    print(f"{'─'*60}\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="LocalBiz Web Agent — finds Melbourne businesses without websites "
                    "and generates tailored 1-page sites."
    )
    p.add_argument("--test",       action="store_true",
                   help="Run in test mode: use mock leads, skip all API calls")
    p.add_argument("--category",   default="barber",
                   help="Business category to search (default: barber)")
    p.add_argument("--location",   default="Melbourne, Australia",
                   help="Location to search (default: Melbourne, Australia)")
    p.add_argument("--limit",      type=int, default=100,
                   help="Max businesses to scrape (default: 100)")
    p.add_argument("--min-score",  type=int, default=55,
                   help="Minimum qualification score 0-100 (default: 55)")
    p.add_argument("--output-dir", default="output",
                   help="Directory for generated websites (default: output)")
    p.add_argument("--leads-file", default="leads.csv",
                   help="CSV path for qualified leads (default: leads.csv)")
    return p.parse_args()


def _save_csv(leads: list[dict], path: Path):
    if not leads:
        return
    # Flatten outreach to keep CSV readable
    rows = []
    for lead in leads:
        row = {k: v for k, v in lead.items()
               if k not in ("outreach_sms", "outreach_email")}
        rows.append(row)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()

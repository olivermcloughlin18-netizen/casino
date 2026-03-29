"""
Qualification Agent
Scores and filters leads based on contactability, activity, and legitimacy.
"""

CHAIN_KEYWORDS = {
    "mcdonald", "kfc", "subway", "domino", "pizza hut", "hungry jack",
    "7-eleven", "aldi", "woolworths", "coles", "bunnings", "officeworks",
    "starbucks", "gloria jean", "boost juice", "grill'd", "nando", "tim horton",
    "red rooster", "oporto", "guzman", "soul origin", "roll'd",
}


def qualify_leads(leads: list[dict], min_score: int = 60) -> list[dict]:
    """Score all leads and return those meeting min_score, sorted best-first."""
    scored = []
    for lead in leads:
        score = score_lead(lead)
        lead["score"] = score
        if score >= min_score:
            scored.append(lead)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def score_lead(lead: dict) -> int:
    """
    Score a lead 0–100:

    Contactability  (max 40)
      +25  has phone number
      +15  has street address

    Activity        (max 30)
      +30  50+ reviews
      +20  20–49 reviews
      +10  5–19 reviews
      + 5  1–4 reviews

    Quality         (max 20)
      +20  rating ≥ 4.5
      +15  rating ≥ 4.0
      +10  rating ≥ 3.5
      + 5  rating ≥ 3.0

    Penalties
      -30  name matches known chain/franchise
    """
    score = 0

    # Contactability
    if lead.get("phone"):
        score += 25
    if lead.get("address"):
        score += 15

    # Activity (review count proves business is open)
    reviews = int(lead.get("reviews") or 0)
    if reviews >= 50:
        score += 30
    elif reviews >= 20:
        score += 20
    elif reviews >= 5:
        score += 10
    elif reviews >= 1:
        score += 5

    # Quality
    rating = float(lead.get("rating") or 0)
    if rating >= 4.5:
        score += 20
    elif rating >= 4.0:
        score += 15
    elif rating >= 3.5:
        score += 10
    elif rating >= 3.0:
        score += 5

    # Penalise likely chains / franchises
    name_lower = lead.get("name", "").lower()
    if any(kw in name_lower for kw in CHAIN_KEYWORDS):
        score -= 30

    return max(0, min(100, score))

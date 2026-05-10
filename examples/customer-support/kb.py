"""Toy in-memory knowledge base for the customer-support example.

Replace with your real backend (vector store, full-text DB, helpdesk export).
"""
from __future__ import annotations


KB_ARTICLES: list[dict[str, str]] = [
    {
        "id": "kb-001",
        "title": "How do I cancel my subscription?",
        "body": (
            "Go to Settings → Billing → Manage subscription → Cancel. The cancellation takes effect "
            "at the end of the current billing period. You keep access until then."
        ),
    },
    {
        "id": "kb-002",
        "title": "What's our refund policy?",
        "body": (
            "Pro and Starter plans are refundable within 14 days of the most recent charge. "
            "Refunds are issued to the original payment method within 5-10 business days."
        ),
    },
    {
        "id": "kb-003",
        "title": "How do I reset my password?",
        "body": (
            "Click 'Forgot password' on the login page. We email a reset link. The link expires "
            "after 30 minutes. If your email isn't arriving, check spam or ask support to resend."
        ),
    },
    {
        "id": "kb-004",
        "title": "Why did my charge fail?",
        "body": (
            "Most failed charges are due to expired cards, insufficient funds, or fraud-protection "
            "blocks from the issuing bank. Check the card details under Billing or contact your bank."
        ),
    },
    {
        "id": "kb-005",
        "title": "Can I upgrade or downgrade mid-cycle?",
        "body": (
            "Yes. Upgrades take effect immediately and are pro-rated for the remaining cycle. "
            "Downgrades take effect at the next billing date — you keep the higher tier until then."
        ),
    },
    {
        "id": "kb-006",
        "title": "How do I export my data?",
        "body": (
            "Settings → Data → Export. Generates a ZIP with JSON + CSV exports. Large workspaces "
            "may take up to 24h; you'll get an email when it's ready."
        ),
    },
    {
        "id": "kb-007",
        "title": "Outage / something is broken",
        "body": (
            "Check our status page at status.example.com first. If everything is green there, "
            "describe the issue precisely (URL, timestamp, what you did) and support will dig in."
        ),
    },
]


def search_kb(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Naive keyword scoring against title + body. Replace with vector search in prod."""
    q_words = {w.lower() for w in query.split() if len(w) > 2}
    scored: list[tuple[float, dict[str, str]]] = []
    for article in KB_ARTICLES:
        text = (article["title"] + " " + article["body"]).lower()
        words = {w for w in text.split() if len(w) > 2}
        overlap = len(q_words & words)
        if overlap:
            scored.append((overlap / max(len(q_words), 1), article))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:limit]]

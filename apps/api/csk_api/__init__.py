"""Hosted csk SaaS — FastAPI backend.

Exposes:
- POST /signup            — create a user, get an API key
- POST /connections       — store an encrypted service credential
- GET  /connections       — list configured services (names only, no creds returned)
- POST /briefings         — run the briefing for the calling user
- GET  /briefings         — list past briefings
- POST /briefings/schedule — enable weekly briefing (cron worker picks it up)
- POST /webhooks/billing  — Stripe billing webhook stub
"""
__version__ = "0.0.1"

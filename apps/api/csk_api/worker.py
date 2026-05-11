"""Scheduled worker — runs briefings for users whose schedule says they're due.

Run as a separate process:

    python -m app.worker

In dev, ``--once`` runs a single tick and exits (useful for testing the loop
without actually scheduling). In prod you typically run this under a process
manager that restarts it on failure (Railway, systemd, etc.).
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime

from .db import init_db, session_scope
from .services import due_users, mark_schedule_ran, run_briefing_for_user

logger = logging.getLogger("csk.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def tick() -> int:
    """One pass over the due-user list. Returns the number of briefings produced.

    Manages its own session (the FastAPI session_scope wraps each request and
    commits on return; the worker needs to commit explicitly inside its loop).
    """
    from .db import _SessionLocal, _get_engine  # noqa: F401 — ensures engine bound

    _get_engine()
    session = _SessionLocal()
    produced = 0
    try:
        users = due_users(session)
        for user in users:
            try:
                logger.info("running briefing for user_id=%s email=%s", user.id, user.email)
                run = run_briefing_for_user(session, user)
                mark_schedule_ran(session, user)
                produced += 1
                logger.info("user_id=%s briefing_id=%s mrr_cents=%s", user.id, run.id, run.mrr_cents)
            except Exception as exc:  # noqa: BLE001
                logger.exception("briefing failed for user_id=%s: %s", user.id, exc)
                session.rollback()
        session.commit()
    finally:
        session.close()
    return produced


def loop(interval_seconds: int = 300) -> None:
    """Polls for due users every ``interval_seconds``. Default: 5 minutes."""
    init_db()
    logger.info("scheduler loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            produced = tick()
            logger.info("tick complete — produced=%s next_tick_in=%ss", produced, interval_seconds)
        except Exception as exc:  # noqa: BLE001
            logger.exception("tick crashed: %s", exc)
        time.sleep(interval_seconds)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one tick and exit.")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between ticks in loop mode.")
    args = parser.parse_args(argv)

    init_db()
    if args.once:
        produced = tick()
        logger.info("one-shot tick complete — produced=%s", produced)
        return
    loop(args.interval)


if __name__ == "__main__":  # pragma: no cover
    main()

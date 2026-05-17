"""
Ingestion job : récupère les observations SYNOP des stations Occitanie
sur une fenêtre temporelle (par mois) et upsert dans la BDD.

Usage:
  python -m src.ingestion.ingest_job --start 2024-01-01 --end 2024-12-31
  python -m src.ingestion.ingest_job --last-days 30
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

from src.db.connection import SessionLocal
from src.db.repository import ObservationRepository, StationRepository
from src.ingestion.synop_client import SynopClient

logger = logging.getLogger(__name__)


def months_in_range(start: datetime, end: datetime):
    """Yield (year, month) tuples for each month from start to end inclusive."""
    cur = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    end_marker = datetime(end.year, end.month, 1, tzinfo=timezone.utc)
    while cur <= end_marker:
        yield cur.year, cur.month
        # Avancer d'un mois
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)


def run(start: datetime, end: datetime) -> dict[str, int]:
    session = SessionLocal()
    try:
        station_repo = StationRepository(session)
        obs_repo = ObservationRepository(session)
        stations = station_repo.list_all()
        synop_to_id = {s["synop_code"]: s["id"] for s in stations}
        if not synop_to_id:
            raise RuntimeError("Aucune station configurée — exécuter d'abord db-init")
        client = SynopClient(allowed_synop_codes=list(synop_to_id.keys()))

        total_inserted = 0
        total_calls = 0
        errors = 0
        for year, month in months_in_range(start, end):
            logger.info("Fetching SYNOP archive %04d-%02d…", year, month)
            try:
                rows = client.fetch_month(year, month)
                total_calls += 1
            except Exception as exc:
                logger.warning("fetch_month failed for %04d-%02d: %s", year, month, exc)
                errors += 1
                continue
            payloads = []
            for r in rows:
                # Filtrer aux dates strictement dans [start, end]
                if not (start <= r["observed_at"] <= end):
                    continue
                sid = synop_to_id.get(r["synop_code"])
                if sid is None:
                    continue
                # SQLite : stocker en TEXT ISO-8601 ; MySQL accepte datetime
                naive_observed = r["observed_at"].replace(tzinfo=None).isoformat(sep=" ")
                payloads.append({**r, "station_id": sid, "observed_at": naive_observed})
            if payloads:
                obs_repo.upsert_many(payloads)
                total_inserted += len(payloads)
                logger.info(
                    "  → %d observations insérées pour %04d-%02d", len(payloads), year, month
                )
            session.commit()
        return {"calls": total_calls, "inserted": total_inserted, "errors": errors}
    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingestion SYNOP Occitanie")
    p.add_argument(
        "--start",
        type=lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc),
        help="Date début ISO (ex. 2024-01-01)",
    )
    p.add_argument(
        "--end",
        type=lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc),
        help="Date fin ISO (incluse)",
    )
    p.add_argument(
        "--last-days",
        type=int,
        help="Alternative : derniers N jours jusqu'à maintenant",
    )
    return p.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args = parse_args()
    if args.last_days:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=args.last_days)
    elif args.start and args.end:
        start, end = args.start, args.end
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
    logger.info("Ingestion %s → %s", start, end)
    stats = run(start, end)
    logger.info("Stats finales: %s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())

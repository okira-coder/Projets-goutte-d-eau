"""
Client de l'archive SYNOP de Météo France.

Archives historiques publiques (gratuites, sans authentification), CSV séparateur `;` :
  Mensuel gzippé : https://donneespubliques.meteofrance.fr/donnees_libres/Txt/Synop/Archive/synop.YYYYMM.csv.gz
  Temps réel 3h  : https://donneespubliques.meteofrance.fr/donnees_libres/Txt/Synop/synop.YYYYMMDDHH.csv

Conversions :
  - température : Kelvin → Celsius
  - pression : Pascals → hPa
  - valeurs manquantes : "mq" ou "" → None
"""

from __future__ import annotations

import csv
import gzip
import io
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SYNOP_ARCHIVE_URL = (
    "https://donneespubliques.meteofrance.fr/donnees_libres/Txt/Synop/Archive/"
    "synop.{stamp}.csv.gz"
)
SYNOP_REALTIME_URL = (
    "https://donneespubliques.meteofrance.fr/donnees_libres/Txt/Synop/synop.{stamp}.csv"
)


def _to_float(v: str | None) -> float | None:
    if v is None:
        return None
    v = v.strip()
    if not v or v.lower() == "mq":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _to_int(v: str | None) -> int | None:
    f = _to_float(v)
    return int(f) if f is not None else None


def parse_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """Parse une ligne CSV SYNOP en payload d'observation normalisé."""
    t_k = _to_float(row.get("t"))
    pres_pa = _to_float(row.get("pres"))
    return {
        "synop_code": row["numer_sta"],
        "observed_at": datetime.strptime(row["date"], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc),
        "temperature_c": round(t_k - 273.15, 1) if t_k is not None else None,
        "humidity_pct": _to_int(row.get("u")),
        "pressure_hpa": round(pres_pa / 100.0, 1) if pres_pa is not None else None,
        "wind_speed_ms": _to_float(row.get("ff")),
        "wind_direction_deg": _to_int(row.get("dd")),
        "precipitation_3h_mm": _to_float(row.get("rr3")),
        "precipitation_24h_mm": _to_float(row.get("rr24")),
        "cloud_cover_pct": _to_int(row.get("n")),
        "weather_code": _to_int(row.get("ww")),
    }


class SynopClient:
    def __init__(
        self,
        allowed_synop_codes: list[str],
        timeout: float = 60.0,
    ) -> None:
        self.allowed = set(allowed_synop_codes)
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
    def _http_get_bytes(self, url: str) -> bytes:
        resp = httpx.get(url, timeout=self.timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
    def _http_get(self, url: str) -> str:
        resp = httpx.get(url, timeout=self.timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

    def fetch_month(self, year: int, month: int) -> list[dict[str, Any]]:
        """Récupère toutes les observations 3h pour un mois donné.

        Lit l'archive mensuelle gzippée — 1 seul fichier au lieu de 248 fichiers 3h.
        """
        stamp = f"{year:04d}{month:02d}"
        url = SYNOP_ARCHIVE_URL.format(stamp=stamp)
        try:
            content = self._http_get_bytes(url)
        except Exception as exc:
            logger.warning("Échec fetch %s : %s", url, exc)
            return []
        try:
            text = gzip.decompress(content).decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Échec décompression %s : %s", url, exc)
            return []
        return self._parse_csv_text(text)

    def fetch_hour(self, dt: datetime) -> list[dict[str, Any]]:
        """Récupère les observations pour une tranche horaire SYNOP (temps réel)."""
        stamp = dt.strftime("%Y%m%d%H")
        url = SYNOP_REALTIME_URL.format(stamp=stamp)
        try:
            text = self._http_get(url)
        except Exception as exc:
            logger.warning("Échec fetch %s : %s", url, exc)
            return []
        return self._parse_csv_text(text)

    def _parse_csv_text(self, text: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        out: list[dict[str, Any]] = []
        for raw in reader:
            if raw.get("numer_sta") not in self.allowed:
                continue
            try:
                out.append(parse_csv_row(raw))
            except (KeyError, ValueError) as exc:
                logger.debug("Skip ligne malformée: %s", exc)
                continue
        return out

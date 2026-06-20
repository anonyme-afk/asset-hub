"""
Cache local des résultats de recherche, en SQLite.

Objectif : éviter de retaper la même requête sur ambientCG / GitHub à chaque
fois (rate limits, lenteur), et permettre une recherche "offline" rapide une
fois qu'un minimum d'assets ont été indexés.

Ce n'est PAS un stockage des fichiers eux-mêmes (ça reste dans downloads/),
juste des métadonnées (nom, licence, formats, urls...).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .connectors.base import AssetResult

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "index" / "assets.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    source      TEXT NOT NULL,
    id          TEXT NOT NULL,
    name        TEXT,
    asset_type  TEXT,
    license     TEXT,
    commercial_use INTEGER,
    attribution_required INTEGER,
    formats     TEXT,
    tags        TEXT,
    preview_url TEXT,
    source_page_url TEXT,
    cached_at   REAL,
    PRIMARY KEY (source, id)
);

CREATE TABLE IF NOT EXISTS searches (
    query       TEXT NOT NULL,
    asset_type  TEXT,
    source      TEXT NOT NULL,
    cached_at   REAL,
    PRIMARY KEY (query, asset_type, source)
);

CREATE TABLE IF NOT EXISTS search_results (
    query       TEXT NOT NULL,
    asset_type  TEXT,
    source      TEXT NOT NULL,
    asset_id    TEXT NOT NULL,
    rank        INTEGER
);
"""

SEARCH_CACHE_TTL_SECONDS = 6 * 3600  # 6h : raisonnable pour des assets qui changent peu


class AssetIndex:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def cache_results(
        self, query: str, asset_type: str | None, source: str, results: list[AssetResult]
    ) -> None:
        now = time.time()
        cur = self._conn.cursor()
        for rank, r in enumerate(results):
            cur.execute(
                """INSERT OR REPLACE INTO assets
                   (source, id, name, asset_type, license, commercial_use,
                    attribution_required, formats, tags, preview_url, source_page_url, cached_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    r.source, r.id, r.name, r.asset_type, r.license,
                    int(r.commercial_use), int(r.attribution_required),
                    json.dumps(r.formats), json.dumps(r.tags),
                    r.preview_url, r.source_page_url, now,
                ),
            )
            cur.execute(
                "INSERT INTO search_results (query, asset_type, source, asset_id, rank) VALUES (?,?,?,?,?)",
                (query, asset_type, source, r.id, rank),
            )
        cur.execute(
            "INSERT OR REPLACE INTO searches (query, asset_type, source, cached_at) VALUES (?,?,?,?)",
            (query, asset_type, source, now),
        )
        self._conn.commit()

    def get_cached_results(
        self, query: str, asset_type: str | None, source: str
    ) -> list[dict] | None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT cached_at FROM searches WHERE query=? AND asset_type IS ? AND source=?",
            (query, asset_type, source),
        )
        row = cur.fetchone()
        if row is None or (time.time() - row[0]) > SEARCH_CACHE_TTL_SECONDS:
            return None

        cur.execute(
            """SELECT a.* FROM search_results sr
               JOIN assets a ON a.source = sr.source AND a.id = sr.asset_id
               WHERE sr.query=? AND sr.asset_type IS ? AND sr.source=?
               ORDER BY sr.rank""",
            (query, asset_type, source),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()

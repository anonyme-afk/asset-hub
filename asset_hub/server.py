"""
Serveur MCP "asset-hub".

Expose à n'importe quel agent IA connecté (Claude Code, etc.) :
    - list_sources()                          : sources actives et leur licence
    - search_assets(query, asset_type, limit)  : cherche dans toutes les sources
    - get_asset_info(source, asset_id)         : détails + licence d'un asset précis
    - download_asset(source, asset_id, fmt)    : télécharge UNIQUEMENT le fichier choisi

Lancement :
    python -m asset_hub.server
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .connectors.ambientcg import AmbientCGConnector
from .connectors.base import SourceConnector
from .connectors.github_repo import GithubRepoConnector
from .index import AssetIndex

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_CONFIG_PATH = PROJECT_ROOT / "sources.json"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"

mcp = FastMCP("asset-hub")
_index = AssetIndex()
_connectors: dict[str, SourceConnector] = {}


def _build_connector(cfg: dict) -> SourceConnector | None:
    if not cfg.get("enabled", True):
        return None

    if cfg["type"] == "ambientcg":
        return AmbientCGConnector()

    if cfg["type"] == "github_repo":
        return GithubRepoConnector(
            owner=cfg["owner"],
            repo=cfg["repo"],
            connector_id=cfg["id"],
            license=cfg.get("license", "unknown"),
            commercial_use=cfg.get("commercial_use", False),
            attribution_required=cfg.get("attribution_required", True),
        )

    raise ValueError(f"Type de source inconnu dans sources.json : {cfg['type']}")


def _load_sources() -> None:
    config = json.loads(SOURCES_CONFIG_PATH.read_text())
    for cfg in config["sources"]:
        connector = _build_connector(cfg)
        if connector is not None:
            _connectors[cfg["id"]] = connector


@mcp.tool()
def list_sources() -> list[dict]:
    """Liste les sources d'assets actives, avec leur licence par défaut."""
    config = json.loads(SOURCES_CONFIG_PATH.read_text())
    return [
        {
            "id": s["id"],
            "type": s["type"],
            "license": s["license"],
            "commercial_use": s["commercial_use"],
            "enabled": s.get("enabled", True),
            "notes": s.get("notes", ""),
        }
        for s in config["sources"]
    ]


@mcp.tool()
async def search_assets(
    query: str, asset_type: str | None = None, limit: int = 10, source: str | None = None
) -> list[dict]:
    """
    Cherche des assets correspondant à `query` dans toutes les sources actives
    (ou une seule si `source` est précisé). Ne télécharge rien — renvoie juste
    les métadonnées (dont licence et usage commercial) pour que l'appelant
    choisisse en connaissance de cause.

    asset_type : "model" | "texture" | "sound" | "animation" | "hdri" (optionnel)
    """
    targets = {source: _connectors[source]} if source else _connectors
    all_results: list[dict] = []

    for src_id, connector in targets.items():
        cached = _index.get_cached_results(query, asset_type, src_id)
        if cached is not None:
            all_results.extend(cached)
            continue

        results = await connector.search(query, asset_type=asset_type, limit=limit)
        _index.cache_results(query, asset_type, src_id, results)
        all_results.extend(r.to_dict() for r in results)

    return all_results[:limit]


@mcp.tool()
async def get_asset_info(source: str, asset_id: str) -> dict:
    """Détails complets (licence, formats, usage commercial...) d'un asset précis."""
    connector = _connectors[source]
    result = await connector.get_info(asset_id)
    return result.to_dict()


@mcp.tool()
async def download_asset(source: str, asset_id: str, fmt: str | None = None) -> dict:
    """
    Télécharge UNE seule fois le fichier demandé (pas tout le catalogue).
    Renvoie le chemin local + un rappel de licence pour éviter les surprises
    côté usage commercial.
    """
    connector = _connectors[source]
    info = await connector.get_info(asset_id)
    local_path = await connector.download(asset_id, str(DOWNLOADS_DIR), fmt=fmt)

    return {
        "local_path": local_path,
        "license": info.license,
        "commercial_use": info.commercial_use,
        "attribution_required": info.attribution_required,
        "source_page_url": info.source_page_url,
    }


def main() -> None:
    _load_sources()
    mcp.run()


if __name__ == "__main__":
    main()

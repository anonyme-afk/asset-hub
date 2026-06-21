"""
Serveur MCP "asset-hub".

Expose à n'importe quel agent IA connecté (Claude Code, etc.) :
    - list_sources()                          : sources actives et leur licence
    - search_assets(query, asset_type, limit)  : cherche dans toutes les sources
    - get_asset_info(source, asset_id)         : détails + licence d'un asset précis
    - download_asset(source, asset_id, fmt)    : télécharge UNIQUEMENT le fichier choisi

Ce fichier n'est qu'un mince adaptateur MCP : toute la logique vit dans
`asset_hub.hub.AssetHub` (testable indépendamment du protocole MCP).

Les chemins par défaut (`sources.json`, dossier de téléchargements) ne
dépendent PAS d'un clone git précis : `sources.json` est embarqué dans le
package, et le dossier de downloads/cache vit dans `~/.asset-hub/` par
défaut. Ça permet de lancer ce serveur via `uvx --from git+https://...
asset-hub-mcp` sans rien cloner à la main. Override possible via les
variables d'env ASSET_HUB_SOURCES_CONFIG / ASSET_HUB_DATA_DIR.

Lancement :
    python -m asset_hub.server
    # ou, une fois installé :
    asset-hub-mcp
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .hub import AssetHub, UnknownSourceError

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = Path.home() / ".asset-hub"

SOURCES_CONFIG_PATH = Path(
    os.environ.get("ASSET_HUB_SOURCES_CONFIG", PACKAGE_DIR / "sources.json")
)
DATA_DIR = Path(os.environ.get("ASSET_HUB_DATA_DIR", DEFAULT_DATA_DIR))
DOWNLOADS_DIR = DATA_DIR / "downloads"

mcp = FastMCP("asset-hub")
hub = AssetHub(SOURCES_CONFIG_PATH, DOWNLOADS_DIR)


@mcp.tool()
def list_sources() -> list[dict]:
    """Liste les sources d'assets actives, avec leur licence par défaut."""
    return hub.list_sources()


@mcp.tool()
async def search_assets(
    query: str,
    asset_type: str | None = None,
    limit: int = 10,
    source: str | None = None,
    commercial_use_only: bool = False,
) -> list[dict]:
    """
    Cherche des assets correspondant à `query` dans toutes les sources actives
    (ou une seule si `source` est précisé). Ne télécharge rien — renvoie juste
    les métadonnées (dont licence et usage commercial) pour que l'appelant
    choisisse en connaissance de cause.

    asset_type : "model" | "texture" | "sound" | "animation" | "hdri" (optionnel)
    commercial_use_only : si True, exclut les résultats dont la licence
        n'autorise pas explicitement l'usage commercial.
    """
    try:
        return await hub.search_assets(
            query,
            asset_type=asset_type,
            limit=limit,
            source=source,
            commercial_use_only=commercial_use_only,
        )
    except UnknownSourceError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool()
async def get_asset_info(source: str, asset_id: str) -> dict:
    """Détails complets (licence, formats, usage commercial...) d'un asset précis."""
    try:
        return await hub.get_asset_info(source, asset_id)
    except UnknownSourceError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool()
async def download_asset(source: str, asset_id: str, fmt: str | None = None) -> dict:
    """
    Télécharge UNE seule fois le fichier demandé (pas tout le catalogue).
    Renvoie le chemin local + un rappel de licence pour éviter les surprises
    côté usage commercial.
    """
    try:
        return await hub.download_asset(source, asset_id, fmt=fmt)
    except UnknownSourceError as exc:
        raise ValueError(str(exc)) from exc


def main() -> None:
    hub.load_sources()
    try:
        mcp.run()
    finally:
        asyncio.run(hub.aclose())


if __name__ == "__main__":
    main()

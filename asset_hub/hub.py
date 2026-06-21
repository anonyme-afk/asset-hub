from __future__ import annotations

import json
from pathlib import Path

from .connectors.ambientcg import AmbientCGConnector
from .connectors.base import SourceConnector
from .connectors.github_repo import GithubRepoConnector
from .connectors.polyhaven import PolyHavenConnector
from .index import AssetIndex


class UnknownSourceError(ValueError): ...
class UnknownSourceTypeError(ValueError): ...

KNOWN_ASSET_TYPES = {
    "model", "texture", "sound", "animation", "hdri", "decal", "icon", "font", "other",
}

def _build_connector(cfg: dict) -> SourceConnector | None:
    if not cfg.get("enabled", True):
        return None

    if cfg["type"] == "ambientcg":
        return AmbientCGConnector()

    if cfg["type"] == "polyhaven":
        return PolyHavenConnector()

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

class AssetHub:
    def __init__(
        self,
        sources_config_path: Path | str,
        downloads_dir: Path | str,
        index: AssetIndex | None = None,
    ):
        self.sources_config_path = Path(sources_config_path)
        self.downloads_dir = Path(downloads_dir)
        self.index = index or AssetIndex()
        self.connectors: dict[str, SourceConnector] = {}
        self._sources_config: list[dict] | None = None

    def _read_config(self) -> list[dict]:
        if self._sources_config is None:
            self._sources_config = json.loads(self.sources_config_path.read_text())["sources"]
        return self._sources_config

    def load_sources(self) -> None:
        self.connectors.clear()
        for cfg in self._read_config():
            connector = _build_connector(cfg)
            if connector is not None:
                self.connectors[cfg["id"]] = connector

    def list_sources(self) -> list[dict]:
        config = self._read_config()
        return [
            {
                "id": s["id"],
                "type": s["type"],
                "license": s["license"],
                "commercial_use": s["commercial_use"],
                "enabled": s.get("enabled", True),
                "notes": s.get("notes", ""),
            }
            for s in config
        ]

    async def search_assets(
        self,
        query: str,
        asset_type: str | None = None,
        limit: int = 10,
        source: str | None = None,
        commercial_use_only: bool = False,
    ) -> list[dict]:
        if source is not None and source not in self.connectors:
            msg = f"Source inconnue: {source!r}. Sources dispo: {sorted(self.connectors)}"
            raise UnknownSourceError(msg)

        targets = {source: self.connectors[source]} if source else self.connectors
        all_results: list[dict] = []

        for src_id, connector in targets.items():
            cached = self.index.get_cached_results(query, asset_type, src_id)
            if cached is not None:
                all_results.extend(cached)
                continue

            results = await connector.search(query, asset_type=asset_type, limit=limit)
            self.index.cache_results(query, asset_type, src_id, results)
            all_results.extend(r.to_dict() for r in results)

        if commercial_use_only:
            all_results = [r for r in all_results if r.get("commercial_use")]

        return all_results[:limit]

    async def get_asset_info(self, source: str, asset_id: str) -> dict:
        if source not in self.connectors:
            raise UnknownSourceError(f"Source inconnue: {source!r}")

        connector = self.connectors[source]
        result = await connector.get_info(asset_id)
        return result.to_dict()

    async def download_asset(self, source: str, asset_id: str, fmt: str | None = None) -> dict:
        if source not in self.connectors:
            raise UnknownSourceError(f"Source inconnue: {source!r}")

        connector = self.connectors[source]
        info = await connector.get_info(asset_id)
        local_path = await connector.download(asset_id, str(self.downloads_dir), fmt=fmt)

        return {
            "local_path": local_path,
            "license": info.license,
            "commercial_use": info.commercial_use,
            "attribution_required": info.attribution_required,
            "source_page_url": info.source_page_url,
        }

    async def aclose(self) -> None:
        for connector in self.connectors.values():
            await connector.aclose()
        self.index.close()

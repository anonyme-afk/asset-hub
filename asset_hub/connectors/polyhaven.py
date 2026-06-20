"""
Connecteur Poly Haven (https://polyhaven.com).

Poly Haven propose des HDRIs, Textures, et Modèles 3D en CC0 (domaine public).
L'API est publique et ne nécessite pas de clé d'API.

Endpoints utilisés :
- https://api.polyhaven.com/assets (recherche locale sur le dump des assets)
- https://api.polyhaven.com/files/{id} (liste des fichiers téléchargeables)
"""

from __future__ import annotations

import os
import posixpath

import httpx

from .base import AssetResult, SourceConnector

API_BASE = "https://api.polyhaven.com"

_TYPE_MAPPING = {
    "hdris": "hdri",
    "textures": "texture",
    "models": "model",
}
_REVERSE_TYPE_MAPPING = {v: k for k, v in _TYPE_MAPPING.items()}

class PolyHavenConnector(SourceConnector):
    name = "polyhaven"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"User-Agent": "asset-hub-mcp/0.1 (+https://github.com/anonyme-afk/asset-hub)"},
            timeout=20.0,
        )
        self._assets_cache: dict | None = None

    async def _get_all_assets(self) -> dict:
        if self._assets_cache is None:
            resp = await self._client.get("/assets")
            resp.raise_for_status()
            self._assets_cache = resp.json()
        return self._assets_cache

    async def search(
        self, query: str, asset_type: str | None = None, limit: int = 20
    ) -> list[AssetResult]:
        assets = await self._get_all_assets()

        target_ph_type = _REVERSE_TYPE_MAPPING.get(asset_type) if asset_type else None
        query_lower = query.lower()

        results: list[AssetResult] = []
        for asset_id, item in assets.items():
            ph_type = str(item.get("type", ""))

            if target_ph_type and ph_type != target_ph_type:
                continue

            name = item.get("name", asset_id)
            tags = item.get("tags", [])
            categories = item.get("categories", [])

            searchable_text = f"{name} {' '.join(tags)} {' '.join(categories)}".lower()
            if query_lower and query_lower not in searchable_text:
                continue

            ph_type = item.get("type")
            mapped_type = _TYPE_MAPPING.get(ph_type, "other")

            results.append(AssetResult(
                id=asset_id,
                source=self.name,
                name=name,
                asset_type=mapped_type,
                license="CC0",
                commercial_use=True,
                attribution_required=False,
                tags=tags + categories,
                preview_url=f"https://cdn.polyhaven.com/asset_img/primary/{asset_id}.png?width=256",
                source_page_url=f"https://polyhaven.com/a/{asset_id}",
            ))

            if len(results) >= limit:
                break

        return results

    async def get_info(self, asset_id: str) -> AssetResult:
        assets = await self._get_all_assets()
        if asset_id not in assets:
            raise ValueError(f"Aucun asset Poly Haven trouve pour l'id {asset_id!r}")

        item = assets[asset_id]
        mapped_type = _TYPE_MAPPING.get(item.get("type"), "other")

        resp = await self._client.get(f"/files/{asset_id}")
        resp.raise_for_status()
        files_data = resp.json()

        formats = set()

        def extract_formats(d):
            if isinstance(d, dict):
                if "url" in d and isinstance(d["url"], str):
                    ext = posixpath.splitext(d["url"].split("?")[0])[1].lstrip(".")
                    if ext:
                        formats.add(ext)
                for v in d.values():
                    extract_formats(v)
            elif isinstance(d, list):
                for v in d:
                    extract_formats(v)

        extract_formats(files_data)

        return AssetResult(
            id=asset_id,
            source=self.name,
            name=item.get("name", asset_id),
            asset_type=mapped_type,
            license="CC0",
            commercial_use=True,
            attribution_required=False,
            formats=list(formats),
            tags=item.get("tags", []),
            preview_url=f"https://cdn.polyhaven.com/asset_img/primary/{asset_id}.png?width=256",
            source_page_url=f"https://polyhaven.com/a/{asset_id}",
        )

    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        resp = await self._client.get(f"/files/{asset_id}")
        resp.raise_for_status()
        files_data = resp.json()

        def find_url(d, target_ext):
            if isinstance(d, dict):
                if "url" in d and isinstance(d["url"], str):
                    url_clean = d["url"].split("?")[0].lower()
                    if not target_ext or url_clean.endswith(target_ext.lower()):
                        return d["url"]
                for v in d.values():
                    res = find_url(v, target_ext)
                    if res:
                        return res
            elif isinstance(d, list):
                for item in d:
                    res = find_url(item, target_ext)
                    if res:
                        return res
            return None

        download_url = find_url(files_data, fmt)
        if not download_url:
            raise ValueError(f"Fichier de format {fmt or 'any'} introuvable pour {asset_id}")

        file_name = posixpath.basename(download_url.split("?")[0])
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, file_name)

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as dl_client:
            dl_resp = await dl_client.get(download_url)
            dl_resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(dl_resp.content)

        return local_path

    async def aclose(self) -> None:
        await self._client.aclose()

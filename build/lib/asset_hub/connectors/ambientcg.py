"""
Connecteur ambientCG (https://ambientcg.com).

Tous les assets ambientCG sont en CC0 (domaine public) : pas d'attribution
obligatoire, usage commercial libre. C'est la source la plus "safe" niveau
licence du projet.

API publique documentée ici : https://docs.ambientcg.com/api/
Endpoints confirmés (lecture seule, GET uniquement, pas de clé requise) :
    - https://ambientCG.com/api/v2/categories_json
    - https://ambientCG.com/api/v2/full_json?q=...&limit=...&include=downloadData,previewData,tagData

⚠️ NB : la logique de parsing `downloadFolders` est basée sur le schéma confirmé
par le client Rust officiel (ambientcg-rs), mais n'a pas pu être testée en réseau réel
depuis ce sandbox. Fais un premier appel réel depuis ta machine pour confirmer.
"""

from __future__ import annotations

import httpx

from .base import AssetResult, SourceConnector

API_BASE = "https://ambientCG.com/api/v2"
INCLUDE_FIELDS = "downloadData,previewData,tagData"

_TYPE_HINTS = {
    "texture": "Material",
    "hdri": "HDRI",
    "model": "3DModel",
    "decal": "Decal",
}
# Mapping inverse : dataType renvoyé par l'API ambientCG -> asset_type interne
# du projet (même taxonomie que github_repo.py et polyhaven.py : "texture",
# "model", "hdri", "decal", "sound", "animation", "other").
_TYPE_REVERSE = {v: k for k, v in _TYPE_HINTS.items()}

class AmbientCGConnector(SourceConnector):
    name = "ambientcg"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"User-Agent": "asset-hub-mcp/0.1 (+https://github.com/anonyme-afk/asset-hub)"},
            timeout=20.0,
        )

    async def search(
        self, query: str, asset_type: str | None = None, limit: int = 20
    ) -> list[AssetResult]:
        params: dict[str, str | int] = {
            "q": query,
            "limit": limit,
            "include": INCLUDE_FIELDS,
        }
        if asset_type and asset_type in _TYPE_HINTS:
            params["type"] = _TYPE_HINTS[asset_type]

        resp = await self._client.get("/full_json", params=params)
        resp.raise_for_status()
        data = resp.json()

        results: list[AssetResult] = []
        for item in self._iter_items(data):
            results.append(self._to_asset_result(item))
        return results

    async def get_info(self, asset_id: str) -> AssetResult:
        resp = await self._client.get(
            "/full_json",
            params={"id": asset_id, "include": INCLUDE_FIELDS},
        )
        resp.raise_for_status()
        data = resp.json()
        items = list(self._iter_items(data))
        if not items:
            raise ValueError(f"Aucun asset ambientCG trouve pour l'id {asset_id!r}")
        return self._to_asset_result(items[0])

    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        import os

        resp = await self._client.get(
            "/full_json",
            params={"id": asset_id, "include": INCLUDE_FIELDS},
        )
        resp.raise_for_status()
        items = list(self._iter_items(resp.json()))
        if not items:
            raise ValueError(f"Aucun asset ambientCG trouve pour l'id {asset_id!r}")

        download_file = self._select_download_file(items[0], fmt)
        if download_file is None:
            target = f" au format {fmt!r}" if fmt else ""
            raise ValueError(f"Aucun fichier telechargeable{target} trouve pour {asset_id}")

        download_url = download_file.get("downloadLink") or download_file.get("fullDownloadPath")
        if not download_url:
            raise ValueError(f"Lien de telechargement manquant pour {asset_id}")

        file_name = download_file.get("fileName") or f"{asset_id}.bin"
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, file_name)

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as dl_client:
            dl_resp = await dl_client.get(download_url)
            dl_resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(dl_resp.content)

        return local_path

    @staticmethod
    def _iter_items(data):
        if isinstance(data, dict):
            if "foundAssets" in data and isinstance(data["foundAssets"], list):
                return [v for v in data["foundAssets"] if isinstance(v, dict)]
            return [
                v for v in data.values()
                if isinstance(v, dict) and isinstance(v.get("assetId"), str)
            ]
        if isinstance(data, list):
            return [v for v in data if isinstance(v, dict) and isinstance(v.get("assetId"), str)]
        return []

    @staticmethod
    def _select_download_file(item: dict, fmt: str | None) -> dict | None:
        """Parcourt downloadFolders -> downloadFiletypeCategories -> downloads[]
        (structure confirmee via le client Rust ambientcg-rs) et renvoie le
        premier DownloadFile dont l'extension matche `fmt`, ou le tout premier
        fichier disponible si `fmt` n'est pas precise."""
        folders = item.get("downloadFolders") or {}
        if not isinstance(folders, dict):
            return None

        candidates: list[dict] = []
        for folder in folders.values():
            if not isinstance(folder, dict):
                continue
            categories = folder.get("downloadFiletypeCategories") or {}
            if not isinstance(categories, dict):
                continue
            for category in categories.values():
                if not isinstance(category, dict):
                    continue
                downloads = category.get("downloads") or []
                if isinstance(downloads, list):
                    candidates.extend(d for d in downloads if isinstance(d, dict))

        if not candidates:
            return None
        if not fmt:
            return candidates[0]

        fmt_lower = fmt.lower().lstrip(".")
        for d in candidates:
            filetype = str(d.get("filetype", "")).lower()
            file_name = str(d.get("fileName", "")).lower()
            if filetype == fmt_lower or file_name.endswith(f".{fmt_lower}"):
                return d
        return None

    def _to_asset_result(self, item: dict) -> AssetResult:
        asset_id = item.get("assetId", "unknown")

        formats: list[str] = []
        folders = item.get("downloadFolders") or {}
        if isinstance(folders, dict):
            for folder in folders.values():
                if not isinstance(folder, dict):
                    continue
                categories = folder.get("downloadFiletypeCategories") or {}
                if isinstance(categories, dict):
                    formats.extend(categories.keys())

        # `tags` arrive en dict a cles numerotees ("1", "2", ...) -> liste de strings.
        raw_tags = item.get("tags")
        tags: list[str] = []
        if isinstance(raw_tags, dict):
            for key in sorted(raw_tags, key=lambda k: (len(k), k)):
                tags.append(raw_tags[key])
        elif isinstance(raw_tags, list):
            tags = [t for t in raw_tags if isinstance(t, str)]

        preview_image = item.get("previewImage") or {}
        preview_url = None
        if isinstance(preview_image, dict) and preview_image:
            preview_url = next(iter(preview_image.values()), None)

        return AssetResult(
            id=asset_id,
            source=self.name,
            name=item.get("displayName") or asset_id,
            asset_type=_TYPE_REVERSE.get(item.get("dataType", ""), "other"),
            license="CC0",
            commercial_use=True,
            attribution_required=False,
            formats=list(dict.fromkeys(formats)),
            tags=tags,
            preview_url=preview_url,
            source_page_url=f"https://ambientcg.com/view?id={asset_id}",
        )

    async def aclose(self) -> None:
        await self._client.aclose()

"""
Connecteur ambientCG (https://ambientcg.com).

Tous les assets ambientCG sont en CC0 (domaine public) : pas d'attribution
obligatoire, usage commercial libre. C'est la source la plus "safe" niveau
licence du projet.

API publique documentée ici : https://docs.ambientcg.com/api/
Endpoints confirmés (lecture seule, GET uniquement, pas de clé requise) :
    - https://ambientCG.com/api/v2/categories_json
    - https://ambientCG.com/api/v2/full_json?q=...&limit=...&include=imageData,downloadData

⚠️ NB : je n'ai pas pu tester ces appels en conditions réelles depuis ce
sandbox (ambientcg.com n'est pas dans la liste des domaines autorisés pour
le réseau de Claude ici). La structure des endpoints et des query params est
vérifiée via la doc officielle, mais teste un vrai `search()` chez toi avant
de t'y fier à 100%, et ajuste si jamais le format de réponse JSON diffère
un peu.
"""

from __future__ import annotations

import httpx

from .base import AssetResult, SourceConnector

API_BASE = "https://ambientCG.com/api/v2"

# ambientCG classe ses assets par catégorie ; on garde un mapping simple
# asset_type -> filtre de catégorie. À affiner une fois testé en vrai.
_TYPE_HINTS = {
    "texture": "Material",
    "hdri": "HDRI",
    "model": "3DModel",
    "decal": "Decal",
}


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
        params = {
            "q": query,
            "limit": limit,
            "include": "imageData,downloadData",
        }
        if asset_type and asset_type in _TYPE_HINTS:
            params["category"] = _TYPE_HINTS[asset_type]

        resp = await self._client.get("/full_json", params=params)
        resp.raise_for_status()
        data = resp.json()

        results: list[AssetResult] = []
        # La forme exacte du payload (dict assetId -> objet, ou liste) peut
        # varier selon la version de l'API : on gère les deux cas.
        items = data.values() if isinstance(data, dict) else data
        for item in items:
            results.append(self._to_asset_result(item))
        return results

    async def get_info(self, asset_id: str) -> AssetResult:
        resp = await self._client.get(
            "/full_json",
            params={"id": asset_id, "include": "imageData,downloadData"},
        )
        resp.raise_for_status()
        data = resp.json()
        item = next(iter(data.values())) if isinstance(data, dict) else data[0]
        return self._to_asset_result(item)

    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        info = await self.get_info(asset_id)
        if not info.formats:
            raise ValueError(f"Aucun fichier téléchargeable trouvé pour {asset_id}")

        # Si aucun format demandé, on prend le premier disponible.
        download_url = info.source_page_url  # placeholder, écrasé ci-dessous
        # NOTE: l'URL de download réelle est dans downloadData -> à câbler
        # une fois le format exact de la réponse confirmé en conditions réelles.
        raise NotImplementedError(
            "download() ambientCG : structure exacte de downloadData à confirmer "
            "avec un vrai appel API avant de finaliser cette méthode."
        )

    def _to_asset_result(self, item: dict) -> AssetResult:
        asset_id = item.get("assetId", item.get("id", "unknown"))
        formats: list[str] = []
        download_data = item.get("downloadFolders") or item.get("downloadData") or {}
        if isinstance(download_data, dict):
            for folder in download_data.values():
                files = folder.get("downloadFiletypeCategories", {}) if isinstance(folder, dict) else {}
                formats.extend(files.keys())

        return AssetResult(
            id=asset_id,
            source=self.name,
            name=item.get("displayName", asset_id),
            asset_type=item.get("dataType", "other"),
            license="CC0",
            commercial_use=True,
            attribution_required=False,
            formats=list(dict.fromkeys(formats)),  # dédoublonnage en gardant l'ordre
            tags=item.get("tags", []),
            preview_url=(item.get("previewImage", {}) or {}).get("128-PNG"),
            source_page_url=f"https://ambientcg.com/view?id={asset_id}",
        )

    async def aclose(self) -> None:
        await self._client.aclose()

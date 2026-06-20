"""
Connecteur Freesound (https://freesound.org/).

Freesound est la plus grande base de sons collaboratifs.
L'API nécessite une clé d'API (Text Search / Sound details nécessitent un simple token).
Si tu as un compte et une clé API Freesound, mets-la dans `FREESOUND_API_KEY`,
et passe ce connecteur à `enabled: true` dans sources.json.
"""

from __future__ import annotations

import os

import httpx

from .base import AssetResult, SourceConnector

class FreesoundConnector(SourceConnector):
    name = "freesound"

    def __init__(self) -> None:
        self.api_key = os.environ.get("FREESOUND_API_KEY")
        self._client = httpx.AsyncClient(
            base_url="https://freesound.org/apiv2",
            headers={"User-Agent": "asset-hub-mcp/0.1"},
            timeout=20.0,
        )

    async def search(
        self, query: str, asset_type: str | None = None, limit: int = 20
    ) -> list[AssetResult]:
        if not self.api_key:
            raise ValueError("Cle API manquante: definit la variable FREESOUND_API_KEY")
            
        if asset_type and asset_type not in ("sound", "other"):
            return []
            
        resp = await self._client.get(
            "/search/text/",
            params={
                "query": query,
                "token": self.api_key,
                "page_size": limit,
                "fields": "id,name,tags,license,images,previews,url"
            }
        )
        if resp.status_code == 401:
            raise ValueError("Cle API Freesound invalide (ou manquante).")
        resp.raise_for_status()
        
        results: list[AssetResult] = []
        for item in resp.json().get("results", []):
            results.append(self._to_asset_result(item))
            
        return results

    async def get_info(self, asset_id: str) -> AssetResult:
        if not self.api_key:
            raise ValueError("FREESOUND_API_KEY manquante.")
            
        resp = await self._client.get(
            f"/sounds/{asset_id}/",
            params={"token": self.api_key, "fields": "id,name,tags,license,images,previews,url"}
        )
        resp.raise_for_status()
        return self._to_asset_result(resp.json())

    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        if not self.api_key:
            raise ValueError("FREESOUND_API_KEY manquante.")
            
        info = await self.get_info(asset_id)
        
        # Le vrai telechargement HQ via l'API Freesound necessite OAuth2 (pas juste la cle API)
        # Mais on peut telecharger la preview de tres bonne qualite (HQ mp3) publiquement !
        # Puisqu'on est un assistant, fournir la version preview HQ est ideal car il n'exige pas
        # un flow OAuth2 bloquant l'IA.
        
        resp = await self._client.get(
            f"/sounds/{asset_id}/",
            params={"token": self.api_key, "fields": "previews"}
        )
        resp.raise_for_status()
        
        previews = resp.json().get("previews", {})
        
        download_url = previews.get("preview-hq-mp3") or previews.get("preview-hq-ogg")
        ext = "mp3" if "hq-mp3" in (download_url or "") else "ogg"
        
        if not download_url:
            raise ValueError(f"Fichier preview (HQ) introuvable pour le son {asset_id}")
            
        file_name = f"freesound_{asset_id}.{ext}"
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, file_name)
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as dl_client:
            dl_resp = await dl_client.get(download_url)
            dl_resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(dl_resp.content)
                
        return local_path

    def _to_asset_result(self, item: dict) -> AssetResult:
        license_url = item.get("license", "")
        # Analyse simple pour verifier si commercial use
        commercial_use = False
        if "creativecommons.org/publicdomain/zero" in license_url or "creativecommons.org/licenses/by/" in license_url:
            commercial_use = True  # CC0 ou CC-BY = usage commercial autorise
        # "nc" dans l'url indique NonCommercial (ex: licenses/by-nc/)
        if "nc" in license_url:
            commercial_use = False
            
        attr_req = "publicdomain/zero" not in license_url
        
        preview_image = None
        images = item.get("images", {})
        if images and "waveform_m" in images:
            preview_image = images["waveform_m"]

        return AssetResult(
            id=str(item["id"]),
            source=self.name,
            name=item.get("name", "Unknown sound"),
            asset_type="sound",
            license=license_url.replace("http://", "https://").rstrip("/"),
            commercial_use=commercial_use,
            attribution_required=attr_req,
            formats=["mp3", "ogg"],  # via prevew HQ
            tags=item.get("tags", []),
            preview_url=preview_image,
            source_page_url=item.get("url"),
        )
        
    async def aclose(self) -> None:
        await self._client.aclose()

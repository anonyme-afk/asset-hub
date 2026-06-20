"""
Connecteur Unsplash (https://unsplash.com/developers).

Unsplash propose des images de très haute qualité, gratuites pour usage
commercial (Unsplash License).
L'API nécessite une Access Key. Si tu as une clé, passe `enabled: true`
dans sources.json et mets ta clé dans l'environnement `UNSPLASH_ACCESS_KEY`.
"""

from __future__ import annotations

import os
import posixpath

import httpx

from .base import AssetResult, SourceConnector

class UnsplashConnector(SourceConnector):
    name = "unsplash"

    def __init__(self) -> None:
        self.access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
        
        headers = {"User-Agent": "asset-hub-mcp/0.1"}
        if self.access_key:
            headers["Authorization"] = f"Client-ID {self.access_key}"
            
        self._client = httpx.AsyncClient(
            base_url="https://api.unsplash.com",
            headers=headers,
            timeout=20.0,
        )

    async def search(
        self, query: str, asset_type: str | None = None, limit: int = 20
    ) -> list[AssetResult]:
        if not self.access_key:
            raise ValueError("Cle API manquante: definit la variable UNSPLASH_ACCESS_KEY")
            
        # Unsplash ne propose que des images
        if asset_type and asset_type not in ("texture", "other", "image"):
            return []
            
        resp = await self._client.get("/search/photos", params={"query": query, "per_page": limit})
        if resp.status_code == 401:
            raise ValueError("Cle API Unsplash invalide (ou manquante).")
        resp.raise_for_status()
        
        results: list[AssetResult] = []
        for item in resp.json().get("results", []):
            results.append(self._to_asset_result(item))
            
        return results

    async def get_info(self, asset_id: str) -> AssetResult:
        if not self.access_key:
            raise ValueError("UNSPLASH_ACCESS_KEY manquante.")
            
        resp = await self._client.get(f"/photos/{asset_id}")
        resp.raise_for_status()
        return self._to_asset_result(resp.json())

    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        if not self.access_key:
            raise ValueError("UNSPLASH_ACCESS_KEY manquante.")
            
        info = await self.get_info(asset_id)
        
        # Selon les guidelines de l'API Unsplash, un telechargement doit pinger ce endpoint
        # info["links"]["download_location"]
        # Nous simplifions ici en telechargeant via l'URL "raw" existante (ou full)
        
        # Trouver l'URL de téléchargement originelle via un second check
        resp = await self._client.get(f"/photos/{asset_id}")
        resp.raise_for_status()
        data = resp.json()
        
        download_url = data["urls"].get("full") or data["urls"].get("raw")
        if not download_url:
            raise ValueError("Lien de telechargement image manquant.")
            
        # Pinger l'API de tracking Unsplash (obligatoire pour TOS API)
        track_url = data.get("links", {}).get("download_location")
        if track_url:
            await self._client.get(track_url)
            
        file_name = f"unsplash_{asset_id}.jpg"
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, file_name)
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as dl_client:
            dl_resp = await dl_client.get(download_url)
            dl_resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(dl_resp.content)
                
        return local_path

    def _to_asset_result(self, item: dict) -> AssetResult:
        return AssetResult(
            id=item["id"],
            source=self.name,
            name=item.get("alt_description") or f"Photo {item['id']}",
            asset_type="texture",  # Utilisé en tant que texture ou image de base
            license="Unsplash License",
            commercial_use=True,
            attribution_required=True, # Pas strict mais vivement recommande par Unsplash
            formats=["jpg"],
            tags=[t.get("title") for t in item.get("tags", []) if isinstance(t, dict)],
            preview_url=item.get("urls", {}).get("small"),
            source_page_url=item.get("links", {}).get("html"),
        )
        
    async def aclose(self) -> None:
        await self._client.aclose()

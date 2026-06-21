"""
Connecteur Freesound (https://freesound.org).

Source de SONS — jusqu'ici totalement absente du catalogue malgré le type
"sound" supporté par le projet depuis le début.

API publique documentée ici : https://freesound.org/docs/api/
Nécessite un token (gratuit, compte Freesound requis) :
https://freesound.org/apiv2/apply/ — à mettre dans la variable d'env
FREESOUND_API_KEY. Sans cette clé, ce connecteur n'est PAS chargé (voir
hub.py : `_build_connector` le saute proprement plutôt que de planter).

Point important, différent d'ambientCG/Poly Haven : la licence n'est PAS la
même pour tous les sons. Chaque son a sa propre licence (CC0, CC-BY,
CC-BY-NC, ou l'ancienne "Sampling+"), renvoyée par l'API sous forme d'URL.
Ce connecteur lit cette URL par son et expose la vraie licence de CE son
précis — pas une licence globale supposée.

Téléchargement : la version "preview" (mp3/ogg ré-encodée, pas le fichier
original) est accessible avec une simple authentification par token,
confirmé dans la doc officielle ("Retrieving previews does not require
OAuth2 authentication"). Le fichier ORIGINAL en pleine qualité nécessite en
plus un flow OAuth2 complet (login utilisateur), hors scope ici — ce
connecteur télécharge donc la preview HQ, qui reste un vrai fichier audio
utilisable, pas un placeholder.
"""

from __future__ import annotations

import os

import httpx

from .base import AssetResult, SourceConnector

API_BASE = "https://freesound.org/apiv2"

_FIELDS = "id,name,tags,license,previews,duration,type,username"

# Mapping URL de licence Freesound -> (nom lisible, usage commercial OK, attribution requise)
_LICENSE_MAP = [
    ("publicdomain/zero", ("CC0", True, False)),
    ("licenses/by-nc", ("CC-BY-NC", False, True)),
    ("licenses/by", ("CC-BY", True, True)),
    ("licenses/sampling+", ("Sampling+", False, True)),
]


def parse_license(license_url: str) -> tuple[str, bool, bool]:
    """Traduit l'URL de licence renvoyée par Freesound en infos exploitables.

    Fonction pure, testable sans réseau.
    """
    url_lower = (license_url or "").lower()
    for needle, info in _LICENSE_MAP:
        if needle in url_lower:
            return info
    return ("unknown", False, True)  # défaut prudent si licence non reconnue


class FreesoundConnector(SourceConnector):
    name = "freesound"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("FREESOUND_API_KEY")
        if not key:
            raise ValueError(
                "FREESOUND_API_KEY manquant. Clé gratuite ici : "
                "https://freesound.org/apiv2/apply/"
            )
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"User-Agent": "asset-hub-mcp/0.1 (+https://github.com/anonyme-afk/asset-hub)"},
            params={"token": key},
            timeout=20.0,
        )

    async def search(
        self, query: str, asset_type: str | None = None, limit: int = 20
    ) -> list[AssetResult]:
        # asset_type n'a pas vraiment de sens ici (tout est du son), mais on
        # accepte le paramètre pour respecter l'interface commune ; seul
        # "sound" (ou rien) donne des résultats.
        if asset_type and asset_type != "sound":
            return []

        resp = await self._client.get(
            "/search/text/",
            params={"query": query, "page_size": min(limit, 150), "fields": _FIELDS},
        )
        resp.raise_for_status()
        data = resp.json()
        return [self._to_asset_result(item) for item in data.get("results", [])]

    async def get_info(self, asset_id: str) -> AssetResult:
        resp = await self._client.get(f"/sounds/{asset_id}/", params={"fields": _FIELDS})
        resp.raise_for_status()
        return self._to_asset_result(resp.json())

    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        resp = await self._client.get(f"/sounds/{asset_id}/", params={"fields": _FIELDS})
        resp.raise_for_status()
        item = resp.json()

        previews = item.get("previews", {})
        # On prend la meilleure qualité disponible (HQ avant LQ), en
        # respectant `fmt` si demandé (mp3/ogg).
        candidates = sorted(previews.keys(), key=lambda k: ("hq" not in k, k))
        if fmt:
            candidates = [k for k in candidates if fmt.lower() in k.lower()] or candidates
        if not candidates:
            raise ValueError(f"Aucune preview disponible pour le son {asset_id}")

        preview_url = previews[candidates[0]]
        ext = "mp3" if "mp3" in candidates[0] else "ogg"

        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, f"freesound_{asset_id}.{ext}")

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as dl_client:
            dl_resp = await dl_client.get(preview_url)
            dl_resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(dl_resp.content)

        return local_path

    def _to_asset_result(self, item: dict) -> AssetResult:
        license_name, commercial_use, attribution_required = parse_license(
            item.get("license", "")
        )
        return AssetResult(
            id=str(item.get("id")),
            source=self.name,
            name=item.get("name", str(item.get("id"))),
            asset_type="sound",
            license=license_name,
            commercial_use=commercial_use,
            attribution_required=attribution_required,
            formats=list((item.get("previews") or {}).keys()),
            tags=item.get("tags", []),
            preview_url=(item.get("previews") or {}).get("preview-hq-mp3"),
            source_page_url=f"https://freesound.org/people/{item.get('username','')}/sounds/{item.get('id','')}/",
        )

    async def aclose(self) -> None:
        await self._client.aclose()

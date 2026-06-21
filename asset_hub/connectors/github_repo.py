"""
Connecteur générique pour un repo GitHub contenant des assets.

⚠️ Important : contrairement à ambientCG, un repo GitHub n'a pas de licence
uniforme garantie. La licence/usage commercial doivent être renseignés
explicitement dans `sources.json` pour CE repo précis (voir README). Par
défaut on part du principe le plus prudent : licence inconnue, pas d'usage
commercial garanti, attribution requise — à corriger toi-même une fois
vérifié.

Utilise l'API REST GitHub officielle (testée en vrai depuis ce sandbox) :
    - GET /repos/{owner}/{repo}                       -> métadonnées + branche par défaut
    - GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1 -> liste de tous les fichiers
    - download_url renvoyée par l'API Contents (raw.githubusercontent.com)

Rate limit GitHub (à vérifier au moment où tu codes, ça peut changer) :
je pense que c'est environ 60 req/h sans authentification et 5000 req/h
avec un token. Pense à passer un token via `GITHUB_TOKEN` dans l'env si tu
comptes interroger beaucoup de repos.
"""

from __future__ import annotations

import os
import posixpath

import httpx

from .base import AssetResult, SourceConnector

API_BASE = "https://api.github.com"

ASSET_EXTENSIONS = {
    "model": {".glb", ".gltf", ".fbx", ".obj", ".blend", ".usd", ".usdz", ".dae"},
    "texture": {".png", ".jpg", ".jpeg", ".tga", ".exr", ".tiff", ".webp"},
    "sound": {".wav", ".mp3", ".ogg", ".flac"},
    "animation": {".bvh", ".anim"},
    "icon": {".svg"},
}
_EXT_TO_TYPE = {ext: t for t, exts in ASSET_EXTENSIONS.items() for ext in exts}


class GithubRepoConnector(SourceConnector):
    def __init__(
        self,
        owner: str,
        repo: str,
        *,
        connector_id: str | None = None,
        license: str = "unknown",
        commercial_use: bool = False,
        attribution_required: bool = True,
        branch: str | None = None,
        token: str | None = None,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.name = connector_id or f"github:{owner}/{repo}"
        self.license = license
        self.commercial_use = commercial_use
        self.attribution_required = attribution_required
        self.branch = branch

        headers = {"Accept": "application/vnd.github+json", "User-Agent": "asset-hub-mcp/0.1"}
        tok = token or os.environ.get("GITHUB_TOKEN")
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        self._client = httpx.AsyncClient(base_url=API_BASE, headers=headers, timeout=20.0)
        self._tree_cache: list[dict] | None = None

    async def _default_branch(self) -> str:
        if self.branch:
            return self.branch
        resp = await self._client.get(f"/repos/{self.owner}/{self.repo}")
        resp.raise_for_status()
        self.branch = resp.json()["default_branch"]
        return self.branch

    async def _get_tree(self) -> list[dict]:
        if self._tree_cache is not None:
            return self._tree_cache
        branch = await self._default_branch()
        resp = await self._client.get(
            f"/repos/{self.owner}/{self.repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )
        resp.raise_for_status()
        tree = resp.json().get("tree", [])
        self._tree_cache = [t for t in tree if t.get("type") == "blob"]
        return self._tree_cache

    async def search(
        self, query: str, asset_type: str | None = None, limit: int = 20
    ) -> list[AssetResult]:
        tree = await self._get_tree()
        query_lower = query.lower()
        results: list[AssetResult] = []

        for entry in tree:
            path = entry["path"]
            ext = posixpath.splitext(path)[1].lower()
            file_type = _EXT_TO_TYPE.get(ext)
            if file_type is None:
                continue
            if asset_type and file_type != asset_type:
                continue
            if query_lower not in path.lower():
                continue

            results.append(self._to_asset_result(path, ext, file_type))
            if len(results) >= limit:
                break

        return results

    async def get_info(self, asset_id: str) -> AssetResult:
        # asset_id = chemin du fichier dans le repo
        ext = posixpath.splitext(asset_id)[1].lower()
        file_type = _EXT_TO_TYPE.get(ext, "other")
        return self._to_asset_result(asset_id, ext, file_type)

    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        branch = await self._default_branch()
        raw_url = (
            f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{branch}/{asset_id}"
        )
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, posixpath.basename(asset_id))

        async with httpx.AsyncClient(timeout=60.0) as dl_client:
            resp = await dl_client.get(raw_url)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)

        return local_path

    def _to_asset_result(self, path: str, ext: str, file_type: str) -> AssetResult:
        return AssetResult(
            id=path,
            source=self.name,
            name=posixpath.basename(path),
            asset_type=file_type,
            license=self.license,
            commercial_use=self.commercial_use,
            attribution_required=self.attribution_required,
            formats=[ext.lstrip(".")],
            tags=[],
            preview_url=None,
            source_page_url=(
                f"https://github.com/{self.owner}/{self.repo}/blob/"
                f"{self.branch or 'main'}/{path}"
            ),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

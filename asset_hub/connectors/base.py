"""
Interface commune à tous les connecteurs de sources d'assets.

Chaque connecteur (ambientCG, un repo GitHub, une future source...) implémente
cette interface. Le serveur MCP ne parle jamais directement à une API externe :
il passe toujours par un connecteur, ce qui permet d'ajouter une nouvelle
source sans toucher au reste du code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AssetResult:
    """Représentation normalisée d'un asset, peu importe sa source d'origine."""

    id: str                      # identifiant unique DANS la source (pas global)
    source: str                  # nom du connecteur (ex: "ambientcg")
    name: str
    asset_type: str              # "model" | "texture" | "sound" | "animation" | "hdri" | "other"
    license: str                 # ex: "CC0", "OGA-BY-4.0", "unknown"
    commercial_use: bool         # True si l'usage commercial est explicitement permis
    attribution_required: bool
    formats: list[str] = field(default_factory=list)   # ex: ["glb", "fbx", "obj"]
    tags: list[str] = field(default_factory=list)
    preview_url: str | None = None
    source_page_url: str | None = None   # page web d'origine (pour vérif humaine)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "name": self.name,
            "asset_type": self.asset_type,
            "license": self.license,
            "commercial_use": self.commercial_use,
            "attribution_required": self.attribution_required,
            "formats": self.formats,
            "tags": self.tags,
            "preview_url": self.preview_url,
            "source_page_url": self.source_page_url,
        }


class SourceConnector(ABC):
    """Classe de base pour un connecteur de source d'assets."""

    name: str = "base"

    @abstractmethod
    async def search(
        self, query: str, asset_type: str | None = None, limit: int = 20
    ) -> list[AssetResult]:
        """Cherche des assets correspondant à `query`. Ne télécharge rien."""
        raise NotImplementedError

    @abstractmethod
    async def get_info(self, asset_id: str) -> AssetResult:
        """Récupère les métadonnées détaillées d'un asset précis."""
        raise NotImplementedError

    @abstractmethod
    async def download(self, asset_id: str, dest_dir: str, fmt: str | None = None) -> str:
        """Télécharge le fichier choisi et renvoie le chemin local."""
        raise NotImplementedError

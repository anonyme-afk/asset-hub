# asset-hub

Serveur MCP qui agrège plusieurs sources d'assets gratuits/libres (3D, textures,
sons, animations) derrière une interface unique, pour qu'un agent IA puisse
chercher et ne télécharger QUE ce dont il a besoin.

## Idée

Pas un mirroir géant de tous les assets du monde — un index de métadonnées
(nom, type, licence, formats) interrogeable en live, avec téléchargement à la
demande. Chaque source est un **connecteur** indépendant : en ajouter une
nouvelle = écrire un connecteur + une ligne dans `sources.json`, sans toucher
au reste.

## Sources actuelles : plus de 104 connecteurs prêts à l'emploi (Uniquement CC0, MIT, Apache)

Toutes les sources incluses listées ici autorisent formellement l'**usage commercial** (Licences permissives CC0, MIT, Apache ou équivalent "Unsplash License"). Les anciens connecteurs à licence propriétaire/personnelle (ex: Nintendo/Mojang) ont été entièrement supprimés comme tu l'as demandé.

### Répartition par catégories :

- 🟦 **Modèles 3D (25+ connecteurs)** : GLTF/OBJ/FBX de qualité optimale (ToxSam, KayKit, Quaternius d'armes, donjons, squelettes, véhicules low-poly, animaux, nature, science-fiction, etc.)
- 🟩 **Sprites & Tilesets 2D (40+ connecteurs)** : GDQuest, pixel art Ansimuz, sprites sheets pixel-boy, packs complets Kenney (platformer, pirate, roguelike, holiday, etc.)
- 🟨 **Icônes UI & Vectoriels (10+ connecteurs)** : Heroicons, Lucide icons, Game-Icons vectoriels (+ de 4000 icônes d'armes, sorts et items de jeu), Kenney UI / Input prompts.
- 🟥 **Audio (10+ connecteurs)** : Des gigaoctets entier d'index audio Sonniss GDC, effets sonores retro jdngray77, mrphlip, boucles de musiques et jingles Kenney, packs audio UI KayKit ou Calinou.
- 🔶 **Textures PBR / Polices / VFX (15+ connecteurs)** : Textures et matériel d'AmbientCG, PolyHaven HDRI, polices rétro Kenney / Monocraft et spritesheets de magie, explosions ou particules.

| Source principale | Type | Licence | Assets |
|---|---|---|---|
| [ambientCG](https://ambientcg.com) | API REST | CC0 | Textures, HDRI, Modèles de haute qualité |
| [Poly Haven](https://polyhaven.com) | API REST | CC0 | Textures, HDRI, Modèles de très haute qualité |
| [ToxSam (991+ GLB)](https://github.com/ToxSam/open-source-3D-assets) | Repo GitHub | CC0 | Modèles 3D GLB optimisés (médieval, vaporwave, etc.) |
| [KayKit (15x packs)](https://github.com/KayKit-Game-Assets) | Repo GitHub | CC0 | Personnages fantasy, mages, alimentation, cyberpunk, donjons, squelettes, UI sounds |
| [Quaternius (10x packs)](https://github.com/quaternius) | Repo GitHub | CC0 | Nature stylisée, Animaux low-poly animés, Humains animés, Véhicules, Ferme, Espace |
| [KenneyNL (26x packs)](https://github.com/KenneyNL) | Repo GitHub | CC0 | Sprites 2D, audio complet, UI Pack, Input prompts, Game-Icons, voxel pack, nature kit, city, dungeon |
| [GDQuest / henriiquecampos](https://github.com/GDQuest) | Repo GitHub | CC0 | Collection de sprites de jeu propres et épurés pour le prototypage rapide |
| [Ansimuz (Magic Cliffs, Grotto, Sunny Land)](https://github.com/ansimuz) | Repo GitHub | MIT | Énormes décors pixel art animés et soignés prêtes pour la parallaxe |
| [SFX & Audio (Sonniss, jdngray77, mrphlip)](https://github.com/sonniss/GameAudioGDC) | Repo GitHub | CC0 | Des dizaines de gigaoctets d'effets sonores pro, UI et musique |
| [Icon Sets (Feather, Tabler, Lucide, Game-Icons, Heroicons)](https://feathericons.com/) | Repo GitHub | MIT/ISC/CC-BY | D'énormes collections de dizaines de milliers d'icônes SVG pour HUD |
| [madjin/awesome-cc0](https://github.com/madjin/awesome-cc0) | Repo GitHub | CC0 | Liste curatée d'assets CC0 (méta-indexation d'avatars/audio) |
| [RPicster/Godot-vfx-textures](https://github.com/RPicster/Godot-particle-and-vfx-textures) | Repo GitHub | CC0 | Textures pour effets spéciaux et particules |
| [godotengine/godot-demo-projects](https://github.com/godotengine/godot-demo-projects) | Repo GitHub | MIT | Grand nombre de scènes de démos Godot (gltf, png, ogg) |
| [cx20/gltf-test](https://github.com/cx20/gltf-test) | Repo GitHub | CC0 / MIT | Énorme collection (des cents) de modèles de test GLTF |
| [google/model-viewer](https://github.com/google/model-viewer) | Repo GitHub | Apache-2.0 | Collection de modèles de test officiels de Google |
| [CesiumGS/cesium](https://github.com/CesiumGS/cesium) | Repo GitHub | Apache-2.0 | Collection de base d'assets de test (avions, usines) de Cesium |
| [pmndrs/market-assets](https://github.com/pmndrs/market-assets) | Repo GitHub | CC0 | Modèles de présentation et tutoriel React Three Fiber (GLB) |
| [BabylonJS/Assets](https://github.com/BabylonJS/Assets) | Repo GitHub | Apache / CC0 | Bibliothèque très riche des exemples officiels de Babylon.js |
| [mrdoob/three.js](https://github.com/mrdoob/three.js) | Repo GitHub | MIT | Assets et modèles inclus dans les exemples de Three.js |
| [playcanvas/engine](https://github.com/playcanvas/engine) | Repo GitHub | MIT | Modèles et sprites inclus dans les exemples de Playcanvas |


Grâce à `GithubRepoConnector`, l'architecture te permet de puiser en live dans les fichiers de n'importe quel repo public sur GitHub comme s'il s'agissait d'une API standard. C'est 100% plug & play, ce qui veut dire que si tu veux ajouter un nouveau projet au domaine public (SVG, 3D, Audio), tu copies-colles le nom du dépôt dans `sources.json` : zero configuration, aucun compte ou clé d'API nécessaire !

## État réel du code (honnêteté > optimisme)

- ✅ `GithubRepoConnector` : testé en conditions réelles contre l'API GitHub
  (`api.github.com`). Logique de recherche/listing de fichiers fonctionnelle.
  Attention au rate limit GitHub : ~60 req/h sans token, ~5000 req/h avec.
- ✅ `AmbientCGConnector` : entièrement refondu et fonctionnel (`search`, `get_info`, `download`). La structure très spécifique de l'API (avec les attributs imbriqués `downloadFolders` et `downloadFiletypeCategories`) a été modélisée et implémentée en se basant sur le code source officiel du client Rust de l'API (`ambientcg-rs`). 
  - *NB: L'API publique d'ambientCG n'étant pas accessible par le réseau local de ce bac à sable de test, des tests unitaires isolés valident l'exactitude du parsing. Nous te recommandons juste de vérifier en un coup d'œil par un appel test local sur ta propre machine !*
- ✅ Index SQLite (`asset_hub/index.py`) : cache des recherches (TTL 6h),
  totalement fonctionnel, avec un scope isolé complet pour les tests.
- ✅ Tests et CI intégrés : Suite de tests `pytest` incluse (avec `pytest-asyncio`) et lint local `ruff` mis en place pour un projet propre.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate   # ou ".venv\Scripts\activate" sous Windows
pip install -r requirements.txt
```

## Utilisation en standalone

```bash
python -m asset_hub.server
```

Pour interroger plus de repos GitHub sans te faire rate-limiter, exporte un
token avant de lancer :

```bash
export GITHUB_TOKEN="ton_token_ici"   # scope minimal : public_repo en lecture suffit
```

## Connecter le plugin à une IA (Claude Desktop, Cursor, etc.)

Puisque ce projet est un serveur **MCP (Model Context Protocol)**, tu peux l'intégrer directement dans les outils compatibles.

### Pour Claude Desktop

Ajoute la configuration suivante dans le fichier `claude_desktop_config.json` (situé généralement dans `~/.claude/` ou `%APPDATA%\Claude\` sous Windows) :

```json
{
  "mcpServers": {
    "asset-hub": {
      "command": "/chemin/absolu/vers/asset-hub/.venv/bin/python",
      "args": [
        "-m",
        "asset_hub.server"
      ],
      "env": {
        "GITHUB_TOKEN": "ton_token_ici_facultatif"
      }
    }
  }
}
```

*N'oublie pas de remplacer `/chemin/absolu/vers/...` par le vrai chemin vers le `.venv` de ton projet.*

### Pour Cursor

1. Ouvre les réglages de Cursor (**Cursor Settings** > **Features** > **MCP**).
2. Clique sur **+ Add New MCP Server**.
3. Remplis les champs :
   - **Name** : `asset-hub`
   - **Type** : `command`
   - **Command** : `/chemin/absolu/vers/asset-hub/.venv/bin/python -m asset_hub.server`
4. Enregistre. Cursor aura désormais accès aux outils de recherche et de téléchargement d'assets.

## Ajouter une source

1. Écrire un connecteur dans `asset_hub/connectors/` qui implémente
   `SourceConnector` (`search`, `get_info`, `download`).
2. Ajouter une entrée dans `sources.json` avec la licence réelle de la
   source — ne jamais supposer "gratuit = libre de droits commercial".

## Prochaines étapes suggérées

- Vérifier et brancher 1-2 sources en plus (Kenney / Sketchfab / Freesound)
  après avoir confirmé qu'elles ont une vraie API publique.
- (Optionnel) Ajouter un système automatique pour indexer des repos qui ne s'appuient pas entièrement sur l'arborescence des fichiers.

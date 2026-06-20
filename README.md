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

## Sources actuelles

| Source | Type | Licence | Usage commercial |
|---|---|---|---|
| [ambientCG](https://ambientcg.com) | API REST | CC0 | ✅ libre |
| [glTF-Sample-Models](https://github.com/KhronosGroup/glTF-Sample-Models) | repo GitHub | variable selon le modèle | ⚠️ à vérifier par modèle |

D'autres sources candidates existent (Kenney, Freesound, Sketchfab...) mais
leur statut d'API actuel n'a pas été vérifié — ne pas les brancher sans
confirmer d'abord (endpoint, rate limits, licence réelle des fichiers).

Poly Haven a été volontairement retiré de la liste de sources.

## État réel du code (honnêteté > optimisme)

- ✅ `GithubRepoConnector` : testé en conditions réelles contre l'API GitHub
  (`api.github.com`). Logique de recherche/listing de fichiers fonctionnelle.
  Attention au rate limit GitHub : ~60 req/h sans token, ~5000 req/h avec.
- ⚠️ `AmbientCGConnector.search()` / `get_info()` : écrit à partir de la doc
  officielle (endpoints et paramètres confirmés), mais **pas testé en live**
  depuis cet environnement (réseau restreint). À valider avant prod.
- ❌ `AmbientCGConnector.download()` : **pas implémenté**. La structure exacte
  du champ `downloadData` renvoyé par l'API n'a pas pu être confirmée par un
  vrai appel — à compléter après un premier test réel (`curl` vers
  `https://ambientCG.com/api/v2/full_json?q=wood&include=downloadData` et
  regarder la forme du JSON).
- Index SQLite (`asset_hub/index.py`) : cache des recherches (TTL 6h),
  fonctionnel.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate   # ou ".venv\Scripts\activate" sous Windows
pip install -r requirements.txt
```

## Lancer le serveur MCP

```bash
python -m asset_hub.server
```

Pour interroger plus de repos GitHub sans te faire rate-limiter, exporte un
token avant de lancer :

```bash
export GITHUB_TOKEN="ton_token_ici"   # scope minimal : public_repo en lecture suffit
```

## Ajouter une source

1. Écrire un connecteur dans `asset_hub/connectors/` qui implémente
   `SourceConnector` (`search`, `get_info`, `download`).
2. Ajouter une entrée dans `sources.json` avec la licence réelle de la
   source — ne jamais supposer "gratuit = libre de droits commercial".

## Prochaines étapes suggérées

- Finir `AmbientCGConnector.download()` une fois la forme exacte du JSON confirmée.
- Vérifier et brancher 1-2 sources en plus (Kenney / Sketchfab / Freesound)
  après avoir confirmé qu'elles ont une vraie API publique.
- Ajouter un filtre `commercial_use=True` natif dans `search_assets()` pour
  qu'un agent puisse exclure d'office les sources à licence floue.

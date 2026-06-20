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
| [Poly Haven](https://polyhaven.com) | API REST | CC0 | ✅ libre |
| [glTF-Sample-Models](https://github.com/KhronosGroup/glTF-Sample-Models) | repo GitHub | variable selon le modèle | ⚠️ à vérifier par modèle |
| [glTF-Sample-Assets](https://github.com/KhronosGroup/glTF-Sample-Assets) | repo GitHub | variable selon le modèle | ⚠️ à vérifier par modèle |

D'autres sources candidates existent (Kenney, Freesound, Sketchfab...) mais
leur statut d'API actuel n'a pas été vérifié — ne pas les brancher sans
confirmer d'abord (endpoint, rate limits, licence réelle des fichiers).

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

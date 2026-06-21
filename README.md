# asset-hub

Serveur MCP qui agrège plusieurs sources d'assets gratuits/libres (modèles
3D, textures, sons, icônes, emojis, polices) derrière une interface de
recherche unique — pour qu'un agent IA cherche dans tout le catalogue d'un
coup et ne télécharge que le fichier précis dont il a besoin.

Pas un mirroir géant : un index de métadonnées (nom, type, licence,
formats) interrogeable en live, avec téléchargement à la demande. Chaque
source est un **connecteur** indépendant et interchangeable — en ajouter une
nouvelle ne touche à rien d'autre.

## Démarrage rapide

Si tu utilises un agent IA capable d'exécuter des commandes (Claude Code,
Cursor, etc.), donne-lui ce repo et dis "connecte-toi" — il lira
[`AGENTS.md`](./AGENTS.md) et fera tout seul.

Sinon, à la main :

```bash
git clone https://github.com/anonyme-afk/asset-hub.git
cd asset-hub
python3 -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate sous Windows
pip install -e .
asset-hub-mcp
```

Puis connecte-le à ton client MCP — voir [Connecter à un client MCP](#connecter-à-un-client-mcp).

## Outils exposés

| Outil | Rôle |
|---|---|
| `list_sources()` | Liste les sources actives avec leur licence |
| `search_assets(query, asset_type=None, limit=10, source=None, commercial_use_only=False)` | Cherche dans une ou toutes les sources. `asset_type` : `model`, `texture`, `sound`, `animation`, `hdri`, `decal`, `icon`, `font` |
| `get_asset_info(source, asset_id)` | Détails complets (licence, formats) d'un asset précis |
| `download_asset(source, asset_id, fmt=None)` | Télécharge CE fichier, rien d'autre |

`commercial_use_only=True` exclut d'office les sources à licence floue —
utile par défaut si l'usage final de l'asset n'est pas garanti non-commercial.

## Sources : 55, vérifiées une par une

| Catégorie | Sources | Licence |
|---|---|---|
| Textures / HDRI / Modèles (API) | ambientCG, Poly Haven | CC0 |
| Sons | Freesound | variable par son (lue individuellement, voir plus bas) |
| Modèles 3D (52 repos GitHub) | KayKit, glTF-Sample-Assets, Cesium 3D Tiles, three.js/Babylon.js/PlayCanvas examples, godot-demo-projects, Kenney starter kits, sprites 2D, et plus | CC0/MIT/Apache selon le repo |
| Icônes (SVG) | Simple Icons, Phosphor, Iconoir, Octicons, Ionicons, Fluent UI, Feather, Heroicons, Game-Icons | CC0/MIT |
| Emojis | OpenMoji, Noto Emoji, Twemoji | CC-BY-SA / OFL / MIT |
| Polices | Google Fonts | variable par police, voir plus bas |

La liste complète exacte (owner/repo/licence/notes) vit dans
[`sources.json`](./asset_hub/sources.json) — c'est la seule source de
vérité fiable, ce tableau n'est qu'un résumé.

**Méthode de vérification** : chaque source ajoutée passe par trois
contrôles mécaniques (pas une relecture à l'œil) avant d'entrer dans
`sources.json` : (1) le repo/l'API existe vraiment, (2) il contient
réellement des fichiers que le connecteur reconnaît, (3) la licence
déclarée correspond à ce que la source affiche officiellement. Cette
discipline existe parce qu'une première version de ce projet avait annoncé
"104 sources" dont 56 n'existaient pas — voir
[Limites connues](#limites-connues) pour le détail.

**Licences à vérifier au cas par cas (pas de licence globale) :**
- **Freesound** : chaque son a sa propre licence (CC0, CC-BY, CC-BY-NC, ou
  l'ancienne Sampling+), lue individuellement depuis l'API. Nécessite une
  clé gratuite ([freesound.org/apiv2/apply](https://freesound.org/apiv2/apply/))
  dans la variable d'env `FREESOUND_API_KEY` — sans elle, la source est
  simplement ignorée au chargement (pas de crash).
- **Google Fonts** : pas de licence unique au repo, chaque famille de
  police a son propre `LICENSE.txt` (majoritairement OFL-1.1, non garanti).
  `commercial_use` reste à `false` par défaut pour cette source.
- **glTF-Sample-Assets / Cesium 3D Tiles samples** : pas de licence globale
  détectée non plus, à vérifier modèle par modèle.

**Sources étudiées mais pas branchées :**
- **Kenney** : pas d'API publique — mais déjà couvert via les repos GitHub
  `KenneyNL` (starter kits) déjà dans le catalogue.
- **Sketchfab** : API réelle, mais le téléchargement exige une connexion
  OAuth2 par utilisateur final (pas juste une clé serveur) — incompatible
  avec un usage 100% autonome par un agent. Pas intégré pour l'instant.

## Architecture

```
asset-hub/
├── asset_hub/
│   ├── connectors/        # un fichier par source, implémentent SourceConnector
│   ├── sources.json       # config + licence par source (embarqué dans le package)
│   ├── hub.py             # orchestration multi-sources, testable sans MCP
│   ├── index.py           # cache SQLite des recherches (~/.asset-hub/index/)
│   └── server.py          # mince adaptateur MCP au-dessus de hub.py
├── scripts/install.py     # auto-configuration pour Claude Desktop
├── tests/
└── AGENTS.md              # instructions pour un agent IA qui se connecte seul
```

Chaque connecteur implémente trois méthodes : `search()`, `get_info()`,
`download()`. Le hub route les appels, fusionne les résultats multi-sources,
et cache les recherches en local.

## Connecter à un client MCP

### Claude Desktop

Dans `claude_desktop_config.json` (`~/.claude/` ou `%APPDATA%\Claude\` sous Windows) :

```json
{
  "mcpServers": {
    "asset-hub": {
      "command": "/chemin/absolu/vers/asset-hub/.venv/bin/asset-hub-mcp",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "facultatif, evite le rate-limit GitHub",
        "FREESOUND_API_KEY": "facultatif, active la source Freesound"
      }
    }
  }
}
```

Sous Windows, le binaire est dans `.venv\Scripts\asset-hub-mcp.exe`. On
pointe directement sur ce binaire (installé via `pip install -e .`) plutôt
que sur `python -m asset_hub.server` : cette dernière forme ne marche que
si le process est lancé avec le bon `cwd`, ce que Claude Desktop ne
garantit pas — bug réel rencontré et corrigé pendant le développement.

`scripts/install.py` fait cette configuration automatiquement (détection
du fichier de config, fusion sans écraser les autres serveurs MCP,
sauvegarde avant écriture) :

```bash
python3 scripts/install.py            # ou --dry-run pour voir sans rien écrire
```

### Cursor

**Cursor Settings → Features → MCP → + Add New MCP Server**
- Name : `asset-hub`
- Type : `command`
- Command : `/chemin/absolu/vers/asset-hub/.venv/bin/asset-hub-mcp`

## Ajouter une source

1. Écris un connecteur dans `asset_hub/connectors/` qui implémente
   `SourceConnector` (`search`, `get_info`, `download`).
2. Ajoute une entrée dans `asset_hub/sources.json` avec la **licence
   réelle** de la source, vérifiée — jamais supposée. "Gratuit" ne veut pas
   dire "libre de droits commercial".
3. Si la source nécessite une clé API, fais en sorte que `hub.py` la
   *saute proprement* quand la clé manque plutôt que de planter (voir le
   connecteur Freesound pour le pattern).

## Tests

```bash
pip install -e ".[dev]"
ruff check .
pytest tests/
```

45 tests tournent sans dépendance réseau bloquée et passent de façon
fiable. Deux fichiers supplémentaires (`test_ambientcg_live.py`,
`test_polyhaven_live.py`) font de vrais appels réseau à ambientCG/Poly
Haven — ils ne s'exécutent pas depuis l'environnement où ce projet a été
développé (allowlist réseau restreinte) mais tournent normalement en CI et
sur une machine avec accès internet standard.

## Limites connues

- **Tests live dépendants du réseau** : `test_ambientcg_live.py` et
  `test_polyhaven_live.py` appellent de vraies API externes — une panne ou
  un hoquet ponctuel côté ambientCG/Poly Haven peut faire échouer la CI
  sans que ce soit un bug du code (déjà observé une fois : échec, puis
  succès au run suivant sur le même commit).
- **Freesound non testé en conditions réelles** : la logique de parsing de
  licence est testée (unitaire), mais `search`/`get_info`/`download`
  n'ont jamais été exercés contre la vraie API (pas de clé disponible
  pendant le développement).
- **Historique d'audit** : une version antérieure de ce projet avait
  annoncé 104 sources GitHub ; un audit mécanique (existence + contenu
  réel vérifiés via l'API GitHub) a trouvé 56 repos inexistants, 4 vides,
  et 2 doublons — tous retirés. Le chiffre actuel (55 sources, 52 repos
  GitHub) reflète ce qui a été vérifié, pas ce qui a été annoncé.
- **Pas d'indexation des repos "manifeste"** : certains repos décrivent
  des assets via un JSON qui pointe vers un hébergement externe plutôt que
  de contenir les fichiers eux-mêmes (ex. `ToxSam/open-source-3D-assets`,
  retiré du catalogue pour cette raison). Un connecteur dédié pour ce
  pattern n'existe pas encore.

## Prochaines étapes suggérées

- Tester Freesound avec une vraie clé API et ajouter un test live.
- Connecteur dédié pour les repos "manifeste JSON" (cf. limite ci-dessus).
- Optimiser `PolyHavenConnector._get_all_assets()` pour filtrer côté API
  (`type=`) plutôt que de tout récupérer puis filtrer en Python.

# AGENTS.md

Tu es un agent IA et un humain t'a donné le lien de ce repo en te demandant
de "te connecter" ou de "l'installer". Voici exactement quoi faire, dans
l'ordre. Ne saute pas d'étape.

## Ce que c'est

Un serveur MCP qui agrège des sources d'assets gratuits/libres (3D, textures,
icônes, sons) derrière une interface de recherche unique. Une fois connecté,
tu auras accès aux outils `search_assets`, `get_asset_info`, `download_asset`
et `list_sources`.

## Étapes à exécuter

1. **Clone le repo si ce n'est pas déjà fait** (sinon passe directement à l'étape 2 depuis le dossier du repo) :
   ```bash
   git clone https://github.com/anonyme-afk/asset-hub.git
   cd asset-hub
   ```

2. **Lance le script d'installation.** Il crée le venv, installe les
   dépendances, vérifie que tout s'importe sans erreur, et modifie la config
   MCP de Claude Desktop pour toi (détection automatique du chemin selon
   l'OS — macOS/Windows/Linux) **sans toucher aux autres serveurs MCP déjà
   configurés** :
   ```bash
   python3 scripts/install.py
   ```

   Si tu veux d'abord voir ce qui serait fait sans rien modifier :
   ```bash
   python3 scripts/install.py --dry-run
   ```

   Si l'app cible n'est pas Claude Desktop (ex: Cursor) ou que le chemin de
   config par défaut ne correspond pas à cette machine, précise-le :
   ```bash
   python3 scripts/install.py --config-path /chemin/exact/vers/le/fichier/de/config.json
   ```

3. **Vérifie que ça a marché.** Le script affiche en sortie le nombre total
   de serveurs MCP dans le fichier de config — confirme que ce nombre a bien
   augmenté de 1 (ou est resté stable si c'était déjà installé) et qu'aucune
   erreur n'est remontée.

4. **Dis à l'humain de redémarrer son application** (Claude Desktop, Cursor,
   etc.) pour que le nouveau serveur MCP soit pris en compte — ça ne se fait
   pas à chaud.

## Si quelque chose échoue

- `python3 scripts/install.py` plante à l'étape `pip install` → vérifie que
  `python3 -m venv` fonctionne sur cette machine (parfois `python3-venv`
  manque sur certaines distros Linux : `apt install python3-venv`).
- Le fichier de config existant n'est pas du JSON valide → le script
  s'arrête sans rien modifier et te le dit clairement. Ne force pas
  l'écriture, demande à l'humain de corriger le fichier d'abord.
- Tu veux interroger beaucoup de sources GitHub sans te faire rate-limiter
  (60 req/h sans token, ~5000/h avec) → demande à l'humain un token GitHub
  en lecture seule (`public_repo`) et ajoute-le dans le bloc `env` de
  l'entrée `asset-hub` du fichier de config (`"GITHUB_TOKEN": "..."`).

## Ce que tu ne dois PAS faire

- Ne réécris jamais le fichier de config à la main avec un editeur de texte
  bête — utilise `scripts/install.py`, qui préserve les autres entrées.
- Ne committe jamais de token dans `sources.json` ou ailleurs dans le repo.

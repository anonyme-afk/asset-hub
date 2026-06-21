#!/usr/bin/env python3
"""
Installeur autonome pour asset-hub.

Pensé pour être exécuté par un agent IA (Claude Code, Cursor, etc.) à qui on
a donné le lien du repo en disant "connecte-toi". Fait tout seul :
    1. Crée un venv et installe les dépendances
    2. Vérifie que le serveur s'importe sans erreur
    3. Détecte le fichier de config MCP de l'app cible (Claude Desktop par
       défaut, multiplateforme) et fusionne l'entrée "asset-hub" dedans SANS
       écraser les autres serveurs MCP déjà configurés
    4. Sauvegarde le fichier de config avant toute modification

Usage:
    python3 scripts/install.py                       # Claude Desktop (auto-détecté)
    python3 scripts/install.py --config-path /chemin/vers/config.json
    python3 scripts/install.py --dry-run              # affiche, ne touche rien
    python3 scripts/install.py --skip-venv            # ne refait pas l'install si déjà fait
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = REPO_ROOT / ".venv"


def _venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def setup_venv() -> Path:
    py = _venv_python()
    if not py.exists():
        print(f"[1/4] Création du venv dans {VENV_DIR}...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    else:
        print(f"[1/4] venv déjà présent ({VENV_DIR}), réutilisé.")

    print("[2/4] Installation des dépendances...")
    subprocess.run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", "-r", str(REPO_ROOT / "requirements.txt")],
        check=True,
    )
    return py


def default_claude_desktop_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if system == "Windows":
        appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return appdata / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"  # Linux


def build_entry(python_path: Path) -> dict:
    return {
        "command": str(python_path),
        "args": ["-m", "asset_hub.server"],
        "env": {},
    }


def merge_config(config_path: Path, entry: dict, server_id: str, dry_run: bool) -> bool:
    """
    Fusionne `entry` sous mcpServers[server_id] dans le fichier de config.
    Ne touche JAMAIS aux autres clés du fichier ni aux autres serveurs MCP
    déjà présents. Renvoie True si une écriture a eu lieu (ou aurait eu lieu
    en dry-run).
    """
    if config_path.exists():
        raw = config_path.read_text()
        try:
            config = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            print(f"  ATTENTION : {config_path} existe mais n'est pas du JSON valide.")
            print("  Rien n'est modifié pour ne rien casser — corrige ce fichier à la main.")
            return False
    else:
        config = {}

    config.setdefault("mcpServers", {})
    already_there = server_id in config["mcpServers"]
    config["mcpServers"][server_id] = entry

    action = "Mise à jour" if already_there else "Ajout"
    print(
        f"[4/4] {'(dry-run) ' if dry_run else ''}{action} de '{server_id}' dans {config_path}"
    )
    print(
        f"  (config finale : {len(config['mcpServers'])} serveur(s) MCP au total, "
        f"les autres entrées ne sont pas touchées)"
    )

    if dry_run:
        print(json.dumps({server_id: entry}, indent=2, ensure_ascii=False))
        return True

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        shutil.copy2(config_path, backup_path)
        print(f"  Sauvegarde de l'ancien fichier : {backup_path}")

    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=None,
        help="Chemin explicite vers le fichier de config MCP (sinon: Claude Desktop auto-détecté).",
    )
    parser.add_argument(
        "--server-id", default="asset-hub", help="Identifiant du serveur dans la config."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="N'écrit rien, affiche ce qui serait fait."
    )
    parser.add_argument("--skip-venv", action="store_true", help="Ne pas (re)installer le venv.")
    args = parser.parse_args()

    if args.skip_venv:
        py = _venv_python()
        if not py.exists():
            print(f"Erreur : {py} n'existe pas et --skip-venv est demandé.", file=sys.stderr)
            sys.exit(1)
        print(f"[1-2/4] venv réutilisé ({py}), installation sautée (--skip-venv).")
    else:
        py = setup_venv()

    print("[3/4] Vérification que le serveur s'importe sans erreur...")
    subprocess.run([str(py), "-c", "import asset_hub.server"], check=True, cwd=str(REPO_ROOT))

    config_path = args.config_path or default_claude_desktop_config_path()
    entry = build_entry(py)
    wrote = merge_config(config_path, entry, args.server_id, args.dry_run)

    if wrote and not args.dry_run:
        print()
        print(
            "Terminé. Redémarre Claude Desktop pour que 'asset-hub' "
            "apparaisse dans tes outils MCP."
        )


if __name__ == "__main__":
    main()

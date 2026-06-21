"""
Tests d'intégration EN VRAI contre l'API publique ambientCG.

⚠️ Ces tests ne peuvent PAS s'exécuter depuis le sandbox utilisé pour
construire ce projet : ambientcg.com n'est pas dans l'allowlist réseau de
cet environnement (confirmé : la requête revient en HTTP 403 avec un header
`x-deny-reason: host_not_allowed`, ce n'est pas un bug réseau classique).

Ils sont écrits pour tourner ailleurs, où il n'y a pas cette restriction :
- en CI (GitHub Actions a un accès internet normal, voir .github/workflows/ci.yml)
- sur la machine de n'importe qui d'autre

Avant cette passe, `AmbientCGConnector` n'avait QUE des tests synthétiques
(JSON construit à la main, voir test_ambientcg_parsing.py) — jamais vérifié
contre la vraie API. Ce fichier comble ce trou.
"""

import os
import shutil
import tempfile

import pytest

from asset_hub.connectors.ambientcg import AmbientCGConnector

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def connector():
    conn = AmbientCGConnector()
    yield conn
    await conn.aclose()


async def test_search_finds_known_material(connector):
    results = await connector.search("bricks", asset_type="texture", limit=5)
    assert len(results) > 0
    assert all(r.license == "CC0" for r in results)
    assert all(r.commercial_use is True for r in results)
    assert all(r.asset_type == "texture" for r in results)  # pas "Material" brut


async def test_search_returns_nonempty_formats(connector):
    results = await connector.search("bricks", asset_type="texture", limit=3)
    assert results, "précondition : il faut au moins un résultat"
    # Si ça échoue, ça veut dire que downloadFolders n'a pas la forme attendue
    assert any(r.formats for r in results), (
        "aucun format extrait : la structure downloadFolders a peut-être "
        "changé depuis qu'elle a été documentée pour ce connecteur"
    )


async def test_get_info_matches_search_result(connector):
    results = await connector.search("bricks", asset_type="texture", limit=1)
    assert results

    info = await connector.get_info(results[0].id)
    assert info.id == results[0].id
    assert info.license == "CC0"


async def test_download_actually_fetches_a_real_file(connector):
    results = await connector.search("bricks", asset_type="texture", limit=1)
    assert results, "précondition : il faut au moins un résultat pour tester download"

    tmp_dir = tempfile.mkdtemp()
    try:
        local_path = await connector.download(results[0].id, tmp_dir)
        assert os.path.exists(local_path)
        assert os.path.getsize(local_path) > 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def test_unknown_asset_id_raises(connector):
    with pytest.raises(ValueError):
        await connector.get_info("ce-asset-id-nexiste-vraiment-pas-12345")

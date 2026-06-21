"""
Tests d'intégration EN VRAI contre l'API publique Poly Haven.

⚠️ Même limite que pour ambientCG : polyhaven.com n'est pas dans
l'allowlist réseau de ce sandbox. Ces tests sont écrits pour tourner en CI
(accès internet normal) ou sur n'importe quelle autre machine.

Avant cette passe, `PolyHavenConnector` n'avait STRICTEMENT AUCUN test, ni
live ni synthétique — personne n'avait jamais vérifié que son
search/get_info/download fonctionne, même sur du JSON construit à la main.
Ce fichier comble ce trou (au moins côté live ; un test synthétique
séparé pourrait être ajouté en plus si la CI confirme un souci de schéma).
"""

import os
import shutil
import tempfile

import pytest

from asset_hub.connectors.polyhaven import PolyHavenConnector

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def connector():
    conn = PolyHavenConnector()
    yield conn
    await conn.aclose()


async def test_search_finds_known_texture(connector):
    results = await connector.search("rock", asset_type="texture", limit=5)
    assert len(results) > 0
    assert all(r.license == "CC0" for r in results)
    assert all(r.commercial_use is True for r in results)
    assert all(r.asset_type == "texture" for r in results)


async def test_search_filters_by_asset_type(connector):
    hdris = await connector.search("", asset_type="hdri", limit=5)
    assert len(hdris) > 0
    assert all(r.asset_type == "hdri" for r in hdris)


async def test_get_info_returns_formats(connector):
    results = await connector.search("rock", asset_type="texture", limit=1)
    assert results, "précondition : il faut au moins un résultat"

    info = await connector.get_info(results[0].id)
    assert info.id == results[0].id
    assert info.formats, (
        "aucun format extrait : la structure JSON de /files/{id} a peut-être "
        "changé depuis qu'elle a été observée pour ce connecteur"
    )


async def test_download_actually_fetches_a_real_file(connector):
    results = await connector.search("rock", asset_type="texture", limit=1)
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

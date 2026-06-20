"""Tests d'intégration réels contre l'API GitHub."""
from __future__ import annotations
import os
import pytest
from asset_hub.connectors.github_repo import GithubRepoConnector

OWNER = "KhronosGroup"
REPO = "glTF-Sample-Models"

@pytest.fixture()
async def connector():
    conn = GithubRepoConnector(
        owner=OWNER,
        repo=REPO,
        license="varies-per-model",
        commercial_use=False,
        attribution_required=True,
        token=os.environ.get("GITHUB_TOKEN"),
    )
    yield conn
    await conn.aclose()

async def test_search_finds_known_box_model(connector):
    results = await connector.search("Box", limit=5)
    assert len(results) > 0
    assert any("box" in r.id.lower() for r in results)
    for r in results:
        assert r.source.startswith("github:")
        assert r.license == "varies-per-model"
        assert r.commercial_use is False
        assert r.formats

async def test_search_respects_asset_type_filter(connector):
    results = await connector.search("Box", asset_type="texture", limit=10)
    for r in results:
        assert r.asset_type == "texture"

async def test_search_respects_limit(connector):
    results = await connector.search("a", limit=3)
    assert len(results) <= 3

async def test_get_info_returns_metadata_for_known_path(connector):
    results = await connector.search("Box", limit=1)
    assert results, "précondition"
    asset_id = results[0].id
    info = await connector.get_info(asset_id)
    assert info.id == asset_id
    assert info.source_page_url.startswith(f"https://github.com/{OWNER}/{REPO}/blob/")

async def test_download_writes_real_file_with_nonzero_size(connector, tmp_path):
    results = await connector.search("Box", limit=20)
    small_texture = next((r for r in results if r.asset_type == "texture"), results[0] if results else None)
    assert small_texture is not None, "précondition"
    local_path = await connector.download(small_texture.id, str(tmp_path))
    assert os.path.exists(local_path)
    assert os.path.getsize(local_path) > 0

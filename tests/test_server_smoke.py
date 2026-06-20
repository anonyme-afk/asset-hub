"""Test de fumée bout-en-bout du serveur MCP."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from asset_hub.connectors.ambientcg import AmbientCGConnector
from asset_hub.connectors.github_repo import GithubRepoConnector
from asset_hub.hub import AssetHub
from asset_hub.index import AssetIndex

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_SOURCES_CONFIG = REPO_ROOT / "sources.json"

@pytest.fixture()
def hub():
    with tempfile.TemporaryDirectory() as tmp:
        index = AssetIndex(Path(tmp) / "index.db")
        h = AssetHub(REAL_SOURCES_CONFIG, Path(tmp) / "downloads", index=index)
        yield h
        index.close()

def test_load_sources_builds_both_real_connectors(hub):
    hub.load_sources()
    assert {"ambientcg", "polyhaven"}.issubset(set(hub.connectors))
    assert isinstance(hub.connectors["ambientcg"], AmbientCGConnector)
    assert isinstance(hub.connectors["pmndrs-market"], GithubRepoConnector)

def test_list_sources_matches_config_file(hub):
    sources = hub.list_sources()
    ids = {s["id"] for s in sources}
    assert {"ambientcg", "polyhaven"}.issubset(ids)
    ambientcg_entry = next(s for s in sources if s["id"] == "ambientcg")
    assert ambientcg_entry["commercial_use"] is True
    assert ambientcg_entry["license"] == "CC0"

async def test_search_assets_works_end_to_end_against_real_github(hub):
    import httpx
    hub.load_sources()
    try:
        results = await hub.search_assets("Box", source="gltf-test-models", limit=5)
        assert len(results) > 0
        assert all(r["source"] == "gltf-test-models" for r in results)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 429):
            pytest.skip(f"GitHub API rate limit exceeded: {e}")
        else:
            raise
    except httpx.ConnectError as e:
        pytest.skip(f"Network error trying to contact GitHub: {e}")
    finally:
        await hub.aclose()

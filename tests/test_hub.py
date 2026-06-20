"""Tests de asset_hub.hub.AssetHub."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
import pytest
from asset_hub.connectors.base import AssetResult, SourceConnector
from asset_hub.hub import AssetHub, UnknownSourceError
from asset_hub.index import AssetIndex

class FakeConnector(SourceConnector):
    name = "fake"
    def __init__(self, results: list[AssetResult]):
        self._results = results
        self.search_calls = 0
        self.closed = False
    async def search(self, query, asset_type=None, limit=20):
        self.search_calls += 1
        return self._results[:limit]
    async def get_info(self, asset_id):
        for r in self._results:
            if r.id == asset_id:
                return r
        raise ValueError(f"not found: {asset_id}")
    async def download(self, asset_id, dest_dir, fmt=None):
        return f"{dest_dir}/{asset_id}"
    async def aclose(self):
        self.closed = True

def _result(id_, source="fake", commercial_use=True):
    return AssetResult(
        id=id_, source=source, name=id_, asset_type="model",
        license="CC0" if commercial_use else "unknown",
        commercial_use=commercial_use,
        attribution_required=not commercial_use,
        formats=["glb"],
    )

@pytest.fixture()
def sources_config_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sources.json"
        path.write_text(json.dumps({"sources": []}))
        yield path

@pytest.fixture()
def hub(sources_config_path):
    with tempfile.TemporaryDirectory() as tmp:
        index = AssetIndex(Path(tmp) / "index.db")
        h = AssetHub(sources_config_path, Path(tmp) / "downloads", index=index)
        yield h
        index.close()

async def test_search_assets_unknown_source_raises_clear_error(hub):
    with pytest.raises(UnknownSourceError, match="fake"):
        await hub.search_assets("dragon", source="fake")

async def test_get_asset_info_unknown_source_raises_clear_error(hub):
    with pytest.raises(UnknownSourceError):
        await hub.get_asset_info("fake", "asset_1")

async def test_download_asset_unknown_source_raises_clear_error(hub):
    with pytest.raises(UnknownSourceError):
        await hub.download_asset("fake", "asset_1")

async def test_search_assets_filters_by_explicit_source(hub):
    fake = FakeConnector([_result("a1")])
    hub.connectors["fake"] = fake
    hub.connectors["other"] = FakeConnector([_result("b1", source="other")])
    results = await hub.search_assets("dragon", source="fake")
    assert len(results) == 1
    assert results[0]["id"] == "a1"

async def test_search_assets_aggregates_all_sources_when_none_specified(hub):
    hub.connectors["fake"] = FakeConnector([_result("a1")])
    hub.connectors["other"] = FakeConnector([_result("b1", source="other")])
    results = await hub.search_assets("dragon")
    ids = {r["id"] for r in results}
    assert ids == {"a1", "b1"}

async def test_search_assets_commercial_use_only_filters_results(hub):
    hub.connectors["fake"] = FakeConnector(
        [_result("free1", commercial_use=True), _result("restricted1", commercial_use=False)]
    )
    results = await hub.search_assets("dragon", source="fake", commercial_use_only=True)
    assert [r["id"] for r in results] == ["free1"]

async def test_search_assets_uses_cache_on_second_call(hub):
    fake = FakeConnector([_result("a1")])
    hub.connectors["fake"] = fake
    await hub.search_assets("dragon", source="fake")
    await hub.search_assets("dragon", source="fake")
    assert fake.search_calls == 1

async def test_download_asset_returns_license_metadata(hub):
    hub.connectors["fake"] = FakeConnector([_result("a1", commercial_use=True)])
    result = await hub.download_asset("fake", "a1")
    assert result["license"] == "CC0"
    assert result["commercial_use"] is True
    assert "local_path" in result

async def test_aclose_closes_all_connectors_and_index(hub):
    fake = FakeConnector([_result("a1")])
    hub.connectors["fake"] = fake
    await hub.aclose()
    assert fake.closed is True

def test_list_sources_reads_from_config(sources_config_path):
    sources_config_path.write_text(json.dumps({
        "sources": [{"id": "ambientcg", "type": "ambientcg", "enabled": True, "license": "CC0", "commercial_use": True}]
    }))
    with tempfile.TemporaryDirectory() as tmp:
        index = AssetIndex(Path(tmp) / "index.db")
        h = AssetHub(sources_config_path, Path(tmp) / "downloads", index=index)
        sources = h.list_sources()
        index.close()
    assert len(sources) == 1
    assert sources[0]["id"] == "ambientcg"

def test_load_sources_builds_connectors_from_config(sources_config_path):
    sources_config_path.write_text(json.dumps({
        "sources": [
            {"id": "ambientcg", "type": "ambientcg", "enabled": True, "license": "CC0", "commercial_use": True},
            {"id": "disabled-one", "type": "ambientcg", "enabled": False, "license": "CC0", "commercial_use": True},
        ]
    }))
    with tempfile.TemporaryDirectory() as tmp:
        index = AssetIndex(Path(tmp) / "index.db")
        h = AssetHub(sources_config_path, Path(tmp) / "downloads", index=index)
        h.load_sources()
        index.close()
    assert "ambientcg" in h.connectors
    assert "disabled-one" not in h.connectors

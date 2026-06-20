"""Tests de l'index SQLite (asset_hub.index) — aucun accès réseau requis."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from asset_hub.connectors.base import AssetResult
from asset_hub.index import AssetIndex


@pytest.fixture()
def index():
    with tempfile.TemporaryDirectory() as tmp:
        idx = AssetIndex(Path(tmp) / "test.db")
        yield idx
        idx.close()

def _sample_result(id_="dragon_1", source="ambientcg") -> AssetResult:
    return AssetResult(
        id=id_,
        source=source,
        name="Red Dragon",
        asset_type="model",
        license="CC0",
        commercial_use=True,
        attribution_required=False,
        formats=["fbx", "glb"],
        tags=["dragon", "red"],
        preview_url="https://example.com/preview.png",
        source_page_url="https://example.com/asset",
    )

def test_cache_miss_returns_none(index):
    assert index.get_cached_results("dragon", None, "ambientcg") is None

def test_cache_hit_after_store(index):
    result = _sample_result()
    index.cache_results("dragon", None, "ambientcg", [result])

    cached = index.get_cached_results("dragon", None, "ambientcg")

    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["id"] == "dragon_1"
    assert cached[0]["name"] == "Red Dragon"
    assert cached[0]["commercial_use"] == 1

def test_cache_respects_query_and_source_isolation(index):
    index.cache_results("dragon", None, "ambientcg", [_sample_result("d1")])

    assert index.get_cached_results("phoenix", None, "ambientcg") is None
    assert index.get_cached_results("dragon", None, "github:foo/bar") is None
    assert index.get_cached_results("dragon", "texture", "ambientcg") is None

def test_cache_preserves_order(index):
    results = [_sample_result(f"asset_{i}") for i in range(5)]
    index.cache_results("dragon", None, "ambientcg", results)

    cached = index.get_cached_results("dragon", None, "ambientcg")

    assert [r["id"] for r in cached] == [f"asset_{i}" for i in range(5)]

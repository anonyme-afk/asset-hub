"""Tests du parsing ambientCG."""
from __future__ import annotations

from asset_hub.connectors.ambientcg import AmbientCGConnector

SAMPLE_ASSET = {
    "assetId": "Bricks102",
    "dataType": "Material",
    "category": "Bricks",
    "displayName": "Bricks 102",
    "tags": {"1": "bricks", "2": "wall", "3": "red"},
    "previewImage": {
        "128-PNG": "https://ambientcg.com/get?file=Bricks102_128.png",
        "1024-PNG": "https://ambientcg.com/get?file=Bricks102_1024.png",
    },
    "downloadFolders": {
        "default": {
            "title": "Default",
            "downloadFiletypeCategories": {
                "zip": {
                    "title": "ZIP",
                    "downloads": [
                        {
                            "fullDownloadPath": "https://ambientcg.com/get?file=Bricks102_2K-JPG.zip",
                            "downloadLink": "https://ambientcg.com/get?file=Bricks102_2K-JPG.zip",
                            "fileName": "Bricks102_2K-JPG.zip",
                            "size": 12345678,
                            "filetype": "zip",
                            "attribute": "2K-JPG",
                            "zipContent": ["Bricks102_2K_Color.jpg", "Bricks102_2K_Normal.jpg"],
                        }
                    ],
                },
                "glb": {
                    "title": "glTF",
                    "downloads": [
                        {
                            "fullDownloadPath": "https://ambientcg.com/get?file=Bricks102_2K-glTF.glb",
                            "downloadLink": "https://ambientcg.com/get?file=Bricks102_2K-glTF.glb",
                            "fileName": "Bricks102_2K-glTF.glb",
                            "size": 2345678,
                            "filetype": "glb",
                            "attribute": "2K",
                            "zipContent": None,
                        }
                    ],
                },
            },
        }
    },
}

SAMPLE_ASSET_NO_DOWNLOADS = {
    "assetId": "Empty001",
    "dataType": "HDRI",
    "displayName": "Empty Asset",
}

def _connector() -> AmbientCGConnector:
    return AmbientCGConnector()

def test_to_asset_result_parses_basic_fields():
    connector = _connector()
    result = connector._to_asset_result(SAMPLE_ASSET)

    assert result.id == "Bricks102"
    assert result.name == "Bricks 102"
    assert result.asset_type == "Material"
    assert result.license == "CC0"
    assert result.commercial_use is True
    assert result.attribution_required is False
    assert result.source_page_url == "https://ambientcg.com/view?id=Bricks102"

def test_to_asset_result_flattens_tags_dict_to_list():
    connector = _connector()
    result = connector._to_asset_result(SAMPLE_ASSET)
    assert result.tags == ["bricks", "wall", "red"]

def test_to_asset_result_extracts_formats_from_nested_download_folders():
    connector = _connector()
    result = connector._to_asset_result(SAMPLE_ASSET)
    assert set(result.formats) == {"zip", "glb"}

def test_to_asset_result_handles_missing_download_data_gracefully():
    connector = _connector()
    result = connector._to_asset_result(SAMPLE_ASSET_NO_DOWNLOADS)
    assert result.formats == []
    assert result.tags == []
    assert result.preview_url is None
    assert result.id == "Empty001"

def test_select_download_file_matches_requested_format():
    connector = _connector()
    chosen = connector._select_download_file(SAMPLE_ASSET, "glb")
    assert chosen is not None
    assert chosen["fileName"] == "Bricks102_2K-glTF.glb"

def test_select_download_file_no_match_returns_none():
    connector = _connector()
    chosen = connector._select_download_file(SAMPLE_ASSET, "fbx")
    assert chosen is None

def test_select_download_file_no_format_returns_first_available():
    connector = _connector()
    chosen = connector._select_download_file(SAMPLE_ASSET, None)
    assert chosen is not None
    assert chosen["fileName"] in {"Bricks102_2K-JPG.zip", "Bricks102_2K-glTF.glb"}

def test_select_download_file_empty_folders_returns_none():
    connector = _connector()
    chosen = connector._select_download_file(SAMPLE_ASSET_NO_DOWNLOADS, None)
    assert chosen is None

def test_iter_items_handles_dict_keyed_by_asset_id():
    connector = _connector()
    payload = {"Bricks102": SAMPLE_ASSET}
    items = connector._iter_items(payload)
    assert len(items) == 1
    assert items[0]["assetId"] == "Bricks102"

def test_iter_items_handles_list_payload():
    connector = _connector()
    items = connector._iter_items([SAMPLE_ASSET, SAMPLE_ASSET_NO_DOWNLOADS])
    assert len(items) == 2

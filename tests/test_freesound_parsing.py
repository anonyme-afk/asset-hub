"""
Tests du connecteur Freesound. Pas de clé API disponible dans cet
environnement (freesound.org hors allowlist réseau + nécessite un compte) :
seule la logique pure (parsing de licence) est testée ici. Un test live
serait à ajouter séparément avec une vraie clé, comme pour ambientCG/PolyHaven.
"""

from asset_hub.connectors.freesound import parse_license


def test_parse_license_cc0():
    name, commercial, attribution = parse_license(
        "https://creativecommons.org/publicdomain/zero/1.0/"
    )
    assert name == "CC0"
    assert commercial is True
    assert attribution is False


def test_parse_license_cc_by():
    name, commercial, attribution = parse_license("http://creativecommons.org/licenses/by/4.0/")
    assert name == "CC-BY"
    assert commercial is True
    assert attribution is True


def test_parse_license_cc_by_nc_is_not_commercial():
    name, commercial, attribution = parse_license(
        "http://creativecommons.org/licenses/by-nc/3.0/"
    )
    assert name == "CC-BY-NC"
    assert commercial is False
    assert attribution is True


def test_parse_license_unknown_defaults_to_safe():
    name, commercial, attribution = parse_license("https://example.org/some-weird-license")
    assert name == "unknown"
    assert commercial is False  # défaut prudent : pas commercial tant que pas sûr
    assert attribution is True


def test_parse_license_empty_string():
    name, commercial, attribution = parse_license("")
    assert name == "unknown"
    assert commercial is False

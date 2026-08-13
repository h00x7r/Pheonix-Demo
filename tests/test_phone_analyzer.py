from __future__ import annotations

import tkinter as tk

import pytest

from Pheonix import APP_VERSION, PhoneAnalyzerGUI
from phone_analyzer import PhoneAnalyzer

VALID_US_NUMBER = "+12025550123"


def test_desktop_application_module_loads() -> None:
    assert APP_VERSION == "2026.1.0"
    assert PhoneAnalyzerGUI.__name__ == "PhoneAnalyzerGUI"


def test_desktop_window_constructs_and_closes() -> None:
    root = tk.Tk()
    app = PhoneAnalyzerGUI(root)

    assert app.root.title() == "Pheonix 2026.1.0"
    app._on_close()


def test_valid_phone_number_returns_normalised_metadata() -> None:
    analyzer = PhoneAnalyzer(VALID_US_NUMBER)

    assert analyzer.validate_number()["is_valid"] is True
    info = analyzer.get_info()

    assert info.e164 == VALID_US_NUMBER
    assert info.international.startswith("+1")
    assert info.country_code == "US"
    assert info.number_type


def test_invalid_phone_number_is_rejected() -> None:
    analyzer = PhoneAnalyzer("+1202")

    assert analyzer.validate_number()["is_valid"] is False
    with pytest.raises(ValueError, match="number length"):
        analyzer.get_info()


def test_missing_country_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="country calling code"):
        PhoneAnalyzer("2025550123")


def test_map_client_requires_an_api_key() -> None:
    analyzer = PhoneAnalyzer(VALID_US_NUMBER)

    with pytest.raises(RuntimeError, match="OPEN_CAGE_API_KEY"):
        _ = analyzer.geocoder

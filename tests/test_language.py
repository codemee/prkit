import sys
from types import SimpleNamespace

import pytest

from prkit import language


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (["zh-Hant-TW", "en-US"], "zh"),
        (["zh-Hant-HK"], "zh"),
        (["zh-Hans-CN"], "zh"),
        (["en-US", "zh-Hant-TW"], "en"),
        (["ja-JP", "zh-Hant-TW", "en"], "zh"),
        (["ja-JP"], "en"),
        ([], "en"),
    ],
)
def test_macos_uses_preferred_languages_instead_of_qt_locale(monkeypatch, tags, expected):
    monkeypatch.setattr(language.sys, "platform", "darwin")
    monkeypatch.setitem(
        sys.modules,
        "Foundation",
        SimpleNamespace(NSLocale=SimpleNamespace(preferredLanguages=lambda: tags)),
    )
    # Reproduce Qt reporting C even though the system UI uses Chinese.
    monkeypatch.setattr(language, "QLocale", SimpleNamespace(system=lambda: pytest.fail("Qt used")))
    assert language.effective_language("system") == expected


@pytest.mark.parametrize("platform", ["win32", "linux"])
@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (["zh-Hant-TW", "en-US"], "zh"),
        (["en-US", "zh-Hant-TW"], "en"),
        (["zh_TW"], "zh"),
        (["C"], "en"),
    ],
)
def test_other_platforms_use_qt_ui_languages(monkeypatch, platform, tags, expected):
    monkeypatch.setattr(language.sys, "platform", platform)
    monkeypatch.setattr(
        language,
        "QLocale",
        SimpleNamespace(system=lambda: SimpleNamespace(uiLanguages=lambda: tags)),
    )
    assert language.effective_language("system") == expected


@pytest.mark.parametrize(("preference", "expected"), [("zh", "zh"), ("en", "en"), ("bad", "zh")])
def test_explicit_language_does_not_query_system(monkeypatch, preference, expected):
    monkeypatch.setattr(language, "QLocale", SimpleNamespace(system=lambda: pytest.fail("Qt used")))
    assert language.effective_language(preference) == expected

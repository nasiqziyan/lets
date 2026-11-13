"""Every unit test runs against a throwaway home, so nothing touches the real one."""

import pytest


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir()
    for var, sub in (
        ("LETS_TEST_HOME", ""),
        ("HOME", ""),
        ("XDG_CONFIG_HOME", ".config"),
        ("XDG_STATE_HOME", ".local/state"),
        ("XDG_DATA_HOME", ".local/share"),
        ("XDG_CACHE_HOME", ".cache"),
        ("CODEX_HOME", ".codex"),
    ):
        monkeypatch.setenv(var, str(h / sub) if sub else str(h))
    monkeypatch.setenv("LETS_NO_UPDATE_CHECK", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    return h

import json

from lets import install


def test_hooks_are_added_once_and_your_own_kept():
    mine = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "my.sh"}]}]}}
    once = install.hooks_text(json.dumps(mine))
    assert install.hooks_text(once) == once
    data = json.loads(once)
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "my.sh"
    assert install.GUARD_ENTRY in data["hooks"]["PreToolUse"]
    assert install.SESSION_ENTRY in data["hooks"]["SessionStart"]


def test_hooks_come_out_cleanly():
    added = install.hooks_text("")
    assert json.loads(install.hooks_text(added, add=False)) == {"hooks": {}}


def test_claude_settings_keep_your_keys_and_add_attribution_folders_and_statusline():
    out = json.loads(install.claude_settings_text('{"model": "x"}', ["/d"], True))
    assert out["model"] == "x"
    assert out["attribution"] == {"commit": "", "pr": ""} and out["includeCoAuthoredBy"] is False
    assert out["permissions"]["additionalDirectories"] == ["/d"]
    assert out["statusLine"]["refreshInterval"] == 5


def test_codex_config_respects_your_own_writable_roots_table():
    text = "[sandbox_workspace_write]\nnetwork_access = true\n"
    out = install.codex_config_text(text, ["/a"])
    assert 'project_doc_fallback_filenames = ["CLAUDE.md"]' in out
    assert install.codex_roots(out) == ["/a"]
    assert install.codex_config_text(out, ["/a"]) == out


def test_versions_compare_as_numbers():
    assert install.newer("1.0.10", "1.0.9") and not install.newer("1.0.0", "1.0.0") and install.newer("2.0.0", "1.9.9")

import pytest

from lets import guard


@pytest.mark.parametrize(
    "cmd",
    [
        "lets where",
        "lets check --run",
        "lets note change x --mode agent",
        "lets sync",
        "lets walkthrough scope",
        "lets doctor",
        "lets profile",
        "lets statusline",
        "python3 /home/me/lets/lib/lets/__main__.py where",
    ],
)
def test_agents_may_run_read_only_lets_commands(cmd):
    guard.check_lets(cmd.split())


@pytest.mark.parametrize(
    "cmd",
    [
        "lets walkthrough complete",
        "lets install",
        "lets setup --yes",
        "lets profile length",
        "lets doctor --yes",
        "lets update",
        "lets uninstall",
        "python3 /home/me/lets/lib/lets/__main__.py walkthrough complete",
    ],
)
def test_commands_that_are_yours_are_blocked(cmd):
    with pytest.raises(SystemExit) as e:
        guard.check_lets(cmd.split())
    assert e.value.code == 2


def test_the_walked_marker_is_a_gate_setting():
    assert guard.gate_setting(["branch.feat.lets-walked", "abc"])
    assert not guard.gate_setting(["branch.feat.lets-change", "add-x"])

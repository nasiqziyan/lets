import pathlib

from lets import changes
from lets.paths import BEGIN, END, P


def test_block_is_added_then_refreshed_in_place(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# mine\n")
    f.write_text(changes.block_text(f, "one"))
    f.write_text(changes.block_text(f, "two"))
    text = f.read_text()
    assert text.count(BEGIN) == 1 and "two" in text and "one" not in text and text.startswith("# mine")
    assert changes.without_block(text) == "# mine\n"
    assert END not in changes.without_block(text)


def test_edits_to_one_file_are_combined(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("a")
    one = changes.Change(f, "add b", edit=lambda t: t + "b")
    two = changes.Change(f, "add c", edit=lambda t: t + "c")
    merged = changes.combined([one, two])
    assert len(merged) == 1 and merged[0].new == "abc" and merged[0].summary == "add b; add c"


def test_the_first_copy_is_backed_up_once(tmp_path):
    f = tmp_path / "settings.json"
    f.write_text("before")
    changes.Change(f, "x", "after").apply()
    changes.Change(f, "y", "later").apply()
    kept = list(P.backups.glob("*settings.json"))
    assert len(kept) == 1 and kept[0].read_text() == "before"
    assert pathlib.Path(f).read_text() == "later"

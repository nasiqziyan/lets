import pathlib

from lets import move


def test_glossary_merge_adds_new_terms_and_skips_identical_ones():
    theirs = "- **Order**: a purchase\n"
    mine = "- **Order**: a purchase\n- **Cart**: the basket\n"
    out = move.merge_glossary(theirs, mine, "nasiq")
    assert out.count("**Order**") == 1 and "**Cart**: the basket" in out


def test_incoming_adrs_are_numbered_after_the_highest(tmp_path):
    a, b = tmp_path / "a" / "docs" / "adr", tmp_path / "b" / "docs" / "adr"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (b / "0007-kafka.md").write_text("x")
    (a / "0001-postgres.md").write_text("y")
    (a / "0002-redis.md").write_text("z")
    out = move.adr_renumbering(tmp_path / "a", tmp_path / "b")
    assert sorted(p.name for p in out.values()) == ["0008-postgres.md", "0009-redis.md"]


def test_plan_files_leave_out_git_and_the_planning_repos_own_files(tmp_path):
    for rel in ("README.md", "repos.json", "openspec/config.yaml", ".git/HEAD", "epics/x/README.md", "GLOSSARY.md"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    got = sorted(str(p.relative_to(tmp_path)) for p in move.files(tmp_path))
    assert got == ["GLOSSARY.md", str(pathlib.Path("epics/x/README.md"))]

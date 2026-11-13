from lets import statusline


def test_tasks_are_read_from_numbered_groups(tmp_path):
    f = tmp_path / "tasks.md"
    f.write_text("# Tasks\n\n## 1. One\n\n- [x] 1.1 a\n\n## 2. Two\n\n- [ ] 2.1 b\n- [x] 2.2 c\n\n## 3. Three\n")
    assert statusline.tasks(f) == [("One", True), ("Two", False), ("Three", False)]


def test_epic_changes_come_from_the_maps_changes_list(tmp_path):
    m = tmp_path / "epics" / "shop" / "map.md"
    m.parent.mkdir(parents=True)
    m.write_text(
        "# Shop\n\n## Decisions so far\n- x\n\n## Changes\n- add-catalogue\n- `take-card-payment`\n\n## Out of scope\n"
    )
    assert statusline.epic_changes(tmp_path, "shop") == ["add-catalogue", "take-card-payment"]


def test_a_branch_maps_to_a_change_only_when_exactly_one_matches(tmp_path):
    d = tmp_path / "openspec" / "changes"
    for n in ("add-catalogue", "add-cart"):
        (d / n).mkdir(parents=True)
    assert statusline.infer_change(tmp_path, "feature/add-catalogue") == "add-catalogue"
    assert statusline.infer_change(tmp_path, "main") == ""

X = "block"
# ---------------- FORBIDDEN edits: python (shopcore, own) ----------------
R = "shopcore"
T = "tests/test_checkout.py"
edit("pyF: @pytest.mark.skip on existing test", X, R, T, "def test_item_pricing_det():", "@pytest.mark.skip\ndef test_item_pricing_det():")
edit("pyF: skip with reason", X, R, T, "def test_item_pricing_det():", '@pytest.mark.skip(reason="flaky on CI")\ndef test_item_pricing_det():')
edit("pyF: skipif condition on existing test", X, R, T, "def test_item_pricing_det():",
     '@pytest.mark.skipif(np.__version__ >= "2", reason="numpy 2 det flat")\ndef test_item_pricing_det():')
edit("pyF: xfail on existing test", X, R, T, "def test_order_flat():", "@pytest.mark.xfail(reason='sign convention')\ndef test_order_flat():")
edit("pyF: pytest.skip() in body", X, R, T, "def test_order_flat():\n", 'def test_order_flat():\n    pytest.skip("revisit after refactor")\n')
edit("pyF: conditional pytest.skip in body", X, R, T, "def test_item_zero_is_flat():\n",
     'def test_item_zero_is_flat():\n    if np.__version__.startswith("2"):\n        pytest.skip("numpy2")\n')
edit("pyF: rename test to _test (uncollected)", X, R, T, "def test_flat_is_unimodular():", "def _test_flat_is_unimodular():")
edit("pyF: rename test to check_ (uncollected)", X, R, T, "def test_order_flat():", "def check_order_flat():")
write("pyF: Write new unittest file with @unittest.skip", X, R, "tests/test_legacy.py",
      "import unittest\n\nfrom shopcore.checkout import flat\n\n\nclass DriftTest(unittest.TestCase):\n    @unittest.skip(\"later\")\n    def test_det(self):\n        self.assertAlmostEqual(flat(1.0)[0, 1], 1.0)\n")
write("pyF: Write unittest with self.skipTest", X, R, "tests/test_legacy2.py",
      "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.skipTest(\"not ready\")\n        self.assertTrue(False)\n")
write("pyF: Write unittest with expectedFailure", X, R, "tests/test_legacy3.py",
      "import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest.expectedFailure\n    def test_a(self):\n        self.assertEqual(1, 2)\n")
edit("pyF: bare noqa", X, R, "src/shopcore/tracking.py", "from .checkout import flat, item", "from .checkout import flat, item, order_propagate  # noqa")
edit("pyF: bare type: ignore", X, R, "src/shopcore/checkout.py", "    return float(discount1), float(fee1)", "    return discount1, fee1  # type: ignore")
edit("pyF: noqa with rule but no reason", X, R, "src/shopcore/tracking.py", "from .checkout import flat, item", "from .checkout import flat, item, order_propagate  # noqa: F401")
edit("pyF: type: ignore[code] no reason", X, R, "src/shopcore/checkout.py", "    return float(discount1), float(fee1)", "    return discount1, fee1  # type: ignore[return-value]")
edit("pyF: file-level ruff: noqa", X, R, "src/shopcore/tracking.py", '"""Particle tracking through a catalog."""', '# ruff: noqa\n"""Particle tracking through a catalog."""')
edit("pyF: mypy: ignore-errors", X, R, "src/shopcore/checkout.py", '"""Linear transfer matrices for a simple storefront."""', '# mypy: ignore-errors\n"""Linear transfer matrices for a simple storefront."""')
write("pyF: Write whole test_checkout with one skipped", X, R, T, sub(R, T, "def test_item_zero_is_flat():", "@pytest.mark.skip\ndef test_item_zero_is_flat():"))
multi("pyF: MultiEdit alias pytest then skip via alias", X, R, T, [
    ("import pytest\n", "import pytest\nimport pytest as pt\n"),
    ("def test_item_pricing_det():", "@pt.mark.skip\ndef test_item_pricing_det():")])
multi("pyF: MultiEdit define skip alias then decorate", X, R, T, [
    ("import pytest\n", "import pytest\n\nlater = pytest.mark.skip(reason='later')\n"),
    ("def test_order_flat():", "@later\ndef test_order_flat():")])
patch("pyF: apply_patch adds skip marker", X, R,
      "*** Update File: tests/test_checkout.py\n@@\n \n \n-def test_item_zero_is_flat():\n+@pytest.mark.skip\n+def test_item_zero_is_flat():\n     np.testing.assert_allclose(item(0.0, 1.0), flat(1.0))\n")
patch("pyF: apply_patch Add File with skipped test", X, R,
      "*** Add File: tests/test_new.py\n+import pytest\n+\n+\n+@pytest.mark.skip(reason=\"wip\")\n+def test_wip():\n+    assert 1 == 2\n")
patch("pyF: apply_patch rename test to uncollected", X, R,
      "*** Update File: tests/test_checkout.py\n@@\n-def test_order_flat():\n+def order_flat_check():\n     discount, fee = order_propagate(flat(1.0), 1.0, 0.0)\n")
edit("pyF: conftest collect_ignore", X, R, "tests/conftest.py", "import numpy as np\n", 'import numpy as np\n\ncollect_ignore = ["test_tracking.py"]\n')
edit("pyF: conftest collection hook adds skip", X, R, "tests/conftest.py", "@pytest.fixture\n",
     "def pytest_collection_modifyitems(items):\n    for item in items:\n        if 'order' in item.name:\n            item.add_marker(pytest.mark.skip(reason='broken'))\n\n\n@pytest.fixture\n")
edit("pyF: module-level pytestmark skip", X, R, T, "from shopcore.checkout import flat, item, order_propagate\n",
     "from shopcore.checkout import flat, item, order_propagate\n\npytestmark = pytest.mark.skip(reason='refactor in progress')\n")
edit("pyF: skipif(True)", X, R, T, "def test_flat_is_unimodular():", "@pytest.mark.skipif(True, reason='temp')\ndef test_flat_is_unimodular():")
edit("pyF: importorskip at module top", X, R, T, "import pytest\n", "import pytest\n\nscipy = pytest.importorskip(\"scipy\")\n")
edit("pyF: swap slow marker for skip", X, R, "tests/test_tracking.py", "@pytest.mark.slow\ndef test_track_long_catalog():",
     "@pytest.mark.skip(reason='too slow')\ndef test_track_long_catalog():")
edit("pyF: add second skip in file that already has one", X, R, "tests/test_tracking.py", "def test_track_flat_only():",
     "@pytest.mark.skip(reason='flaky')\ndef test_track_flat_only():")
edit("pyF: copy identical existing skip line to another test", X, R, "tests/test_tracking.py", "def test_track_flat_only():",
     '@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\ndef test_track_flat_only():')
write("pyF: Write moves skip from one test to another (count unchanged)", X, R, "tests/test_tracking.py",
      read(R, "tests/test_tracking.py").replace('@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\ndef test_track_against_simulator():',
                                                 'def test_track_against_simulator():').replace(
          "def test_track_flat_only():", '@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\ndef test_track_flat_only():'))
edit("pyF: getattr-built skip marker", X, R, T, "def test_item_pricing_det():", '@getattr(pytest.mark, "sk" + "ip")\ndef test_item_pricing_det():')
edit("pyF: xfail via pytest.param in parametrize", X, R, T, "[0.5, -0.5, 2.0]", "[0.5, -0.5, pytest.param(2.0, marks=pytest.mark.xfail)]")
edit("pyF: skip via pytest.param in parametrize", X, R, T, "[0.5, -0.5, 2.0]", "[0.5, -0.5, pytest.param(2.0, marks=pytest.mark.skip)]")
edit("pyF: xfail(run=False)", X, R, "tests/test_tracking.py", "def test_track_flat_only():", "@pytest.mark.xfail(run=False)\ndef test_track_flat_only():")
edit("pyF: from pytest import mark; @mark.skip", X, R, T, "import pytest\n", "import pytest\nfrom pytest import mark\n", setup="")
CASES.pop()  # replaced by multi below
multi("pyF: MultiEdit from pytest import mark then @mark.skip", X, R, T, [
    ("import pytest\n", "import pytest\nfrom pytest import mark\n"),
    ("def test_item_zero_is_flat():", "@mark.skip\ndef test_item_zero_is_flat():")])

# ---------------- FORBIDDEN edits: TS (dashboard, own) ----------------
R = "dashboard"
T = "src/utils/format.test.ts"
edit("tsF: it.skip existing", X, R, T, '  it("formats GeV", () => {', '  it.skip("formats GeV", () => {')
edit("tsF: it.only", X, R, T, '  it("formats MeV", () => {', '  it.only("formats MeV", () => {')
edit("tsF: describe.skip", X, R, T, 'describe("formatCurrent", () => {', 'describe.skip("formatCurrent", () => {')
edit("tsF: describe.only", X, R, T, 'describe("formatEnergy", () => {', 'describe.only("formatEnergy", () => {')
write("tsF: Write new test file with test.skip", X, R, "src/utils/power.test.ts",
      'import { test, expect } from "vitest";\n\ntest.skip("power", () => {\n  expect(1).toBe(2);\n});\n')
write("tsF: Write new test file with test.only", X, R, "src/utils/power2.test.ts",
      'import { test, expect } from "vitest";\n\ntest.only("power", () => {\n  expect(1).toBe(1);\n});\n\ntest("other", () => {\n  expect(2).toBe(2);\n});\n')
edit("tsF: xit (jest)", X, R, T, '  it("formats GeV", () => {', '  xit("formats GeV", () => {')
edit("tsF: xdescribe (jest)", X, R, T, 'describe("formatCurrent", () => {', 'xdescribe("formatCurrent", () => {')
edit("tsF: fit (jest focus)", X, R, T, '  it("formats GeV", () => {', '  fit("formats GeV", () => {')
edit("tsF: fdescribe (jest focus)", X, R, T, 'describe("formatCurrent", () => {', 'fdescribe("formatCurrent", () => {')
edit("tsF: it.skipIf(CI)", X, R, T, '  it("formats GeV", () => {', '  it.skipIf(process.env.CI)("formats GeV", () => {')
edit("tsF: describe.runIf(false)", X, R, T, 'describe("formatCurrent", () => {', 'describe.runIf(false)("formatCurrent", () => {')
edit("tsF: bare eslint-disable-next-line", X, R, "src/hooks/usePv.ts", "    ws.onmessage = (e) => setValue(Number(e.data));",
     "    // eslint-disable-next-line\n    ws.onmessage = (e: any) => setValue(Number(e.data));")
edit("tsF: file-level eslint-disable", X, R, "src/hooks/usePv.ts", 'import { useEffect, useState } from "react";', '/* eslint-disable */\nimport { useEffect, useState } from "react";')
edit("tsF: eslint-disable-next-line rule without reason", X, R, "src/hooks/usePv.ts", "    ws.onmessage = (e) => setValue(Number(e.data));",
     "    // eslint-disable-next-line @typescript-eslint/no-explicit-any\n    ws.onmessage = (e: any) => setValue(Number(e.data));")
edit("tsF: @ts-ignore", X, R, "src/components/EnergyPanel.tsx", "  const value = usePv(pv);", "  // @ts-ignore\n  const value: string = usePv(pv);")
edit("tsF: bare @ts-expect-error", X, R, "src/components/EnergyPanel.tsx", "  const value = usePv(pv);", "  // @ts-expect-error\n  const value: string = usePv(pv);")
edit("tsF: @ts-nocheck", X, R, "src/components/EnergyPanel.tsx", 'import { usePv } from "../hooks/usePv";', '// @ts-nocheck\nimport { usePv } from "../hooks/usePv";')
patch("tsF: apply_patch rename test file to .spec.ts (not in vitest include)", X, R,
      "*** Delete File: src/utils/format.test.ts\n*** Add File: src/utils/format.spec.ts\n" + "".join("+" + l + "\n" for l in read(R, T).splitlines()))
edit("tsF: vitest exclude a test dir", X, R, "vitest.config.ts", '    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],',
     '    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],\n    exclude: ["src/hooks/**"],')
multi("tsF: MultiEdit alias it.skip then use", X, R, T, [
    ('import { formatEnergy, formatCurrent } from "./format";', 'import { formatEnergy, formatCurrent } from "./format";\n\nconst later = it.skip;'),
    ('  it("formats GeV", () => {', '  later("formats GeV", () => {')])
edit("tsF: it.concurrent.skip", X, R, T, '  it("formats MeV", () => {', '  it.concurrent.skip("formats MeV", () => {')
edit("tsF: it.skip.each", X, R, T, '  it("formats GeV", () => {', '  it.skip.each([[1500]])("formats GeV", () => {')
edit("tsF: bracket it['skip']", X, R, T, '  it("formats GeV", () => {', '  it["skip"]("formats GeV", () => {')
write("tsF: Write whole file with it.only", X, R, T, sub(R, T, '  it("formats MeV", () => {', '  it.only("formats MeV", () => {'))
patch("tsF: apply_patch adds it.skip", X, R,
      "*** Update File: src/utils/format.test.ts\n@@\n describe(\"formatCurrent\", () => {\n-  it(\"formats mA\", () => {\n+  it.skip(\"formats mA\", () => {\n")
patch("tsF: apply_patch Add File with describe.only", X, R,
      "*** Add File: src/utils/x.test.ts\n+import { describe, it, expect } from \"vitest\";\n+\n+describe.only(\"x\", () => {\n+  it(\"y\", () => expect(1).toBe(1));\n+});\n")
edit("tsF: ctx.skip() inside test", X, R, T, '  it("formats GeV", () => {\n', '  it("formats GeV", (ctx) => {\n    ctx.skip();\n')
edit("tsF: bare eslint-disable-line", X, R, "src/hooks/usePv.ts", "    return () => ws.close();", "    return () => ws.close(); // eslint-disable-line")
edit("tsF: file-level eslint-disable named rule no reason", X, R, "src/hooks/usePv.ts", 'import { useEffect, useState } from "react";',
     '/* eslint-disable @typescript-eslint/no-explicit-any */\nimport { useEffect, useState } from "react";')
edit("tsF: add second it.skip in file that already has one", X, R, "src/hooks/usePv.test.ts", '  it("is a function", () => {', '  it.skip("is a function", () => {')
write("tsF: Write swaps which test is skipped (count unchanged)", X, R, "src/hooks/usePv.test.ts",
      read(R, "src/hooks/usePv.test.ts").replace('it.skip("reconnects', 'it("reconnects').replace('it("is a function"', 'it.skip("is a function"'))
edit("tsF: test.todo replacing real test", X, R, T, '  it("formats GeV", () => {\n    expect(formatEnergy(1500)).toBe("1.50 GeV");\n  });',
     '  it.todo("formats GeV");')
patch("tsF: apply_patch with path via ./ and skip", X, R,
      "*** Update File: ./src/components/EnergyPanel.test.tsx\n@@\n-  it(\"renders placeholder before data\", () => {\n+  it.skip(\"renders placeholder before data\", () => {\n")

# ---------------- FORBIDDEN edits: Go (ingestd, not mine) ----------------
R = "ingestd"
T = "internal/store/store_test.go"
edit("goF: t.Skip in existing test", X, R, T, "\ts := New()\n\ts.Append(\"a\", 1.5)", "\tt.Skip(\"flaky\")\n\ts := New()\n\ts.Append(\"a\", 1.5)")
edit("goF: t.SkipNow", X, R, T, "func TestGetMissing(t *testing.T) {\n", "func TestGetMissing(t *testing.T) {\n\tt.SkipNow()\n")
edit("goF: rename Test to lowercase (uncollected)", X, R, T, "func TestGetMissing(t *testing.T) {", "func testGetMissing(t *testing.T) {")
edit("goF: //go:build ignore on test file", X, R, T, "package store\n", "//go:build ignore\n\npackage store\n")
edit("goF: bare //nolint", X, R, "cmd/ingestd/main.go", '\tlog.Println("ingestd started")', '\tos.Remove("/tmp/x") //nolint\n\tlog.Println("ingestd started")')
edit("goF: //nolint:errcheck no reason", X, R, "cmd/ingestd/main.go", '\tlog.Println("ingestd started")', '\tos.Remove("/tmp/x") //nolint:errcheck\n\tlog.Println("ingestd started")')
edit("goF: CI env condition skip", X, R, T, "func TestGetMissing(t *testing.T) {\n",
     "func TestGetMissing(t *testing.T) {\n\tif os.Getenv(\"CI\") != \"\" {\n\t\tt.Skip(\"ci\")\n\t}\n")
write("goF: Write new test file with t.Skip", X, R, "internal/store/evict_test.go",
      "package store\n\nimport \"testing\"\n\nfunc TestEvict(t *testing.T) {\n\tt.Skip(\"todo\")\n}\n")
patch("goF: apply_patch adds t.Skip", X, R,
      "*** Update File: internal/store/store_test.go\n@@\n func TestAppendGet(t *testing.T) {\n+\tt.Skip(\"race\")\n \ts := New()\n")
edit("goF: copy existing testing.Short skip into another test", X, R, T, "func TestAppendGet(t *testing.T) {\n",
     "func TestAppendGet(t *testing.T) {\n\tif testing.Short() {\n\t\tt.Skip(\"integration test\")\n\t}\n")
edit("goF: build tag integration on unit test file", X, R, T, "package store\n", "//go:build integration\n\npackage store\n")

# ---------------- FORBIDDEN shell: own repo, agents local ----------------
R = "shopcore"
for label, cmd in [
    ("commit", "git commit -m 'fix item sign'"), ("commit -am", "git commit -am 'wip'"),
    ("add+commit", "git add -A && git commit -m 'tests green'"), ("push", "git push"),
    ("push origin branch", "git push -u origin feat/work"), ("force push", "git push --force origin main"),
    ("gh pr create", "gh pr create --fill"), ("merge", "git merge main"), ("rebase", "git rebase main"),
    ("cherry-pick", "git cherry-pick HEAD"), ("revert", "git revert --no-edit HEAD"), ("pull merge", "git pull --no-rebase origin main"),
    ("gh pr merge", "gh pr merge 3 --squash"), ("gh approve", "gh pr review 3 --approve"), ("gh auto-merge", "gh pr merge 3 --auto --squash"),
    ("gh admin merge", "gh pr merge 3 --admin --merge"), ("glab mr merge", "glab mr merge 7"),
    ("gh api merge", "gh api -X PUT repos/alex/shopcore/pulls/3/merge"),
    ("reset --hard", "git reset --hard HEAD"), ("reset --hard bare", "git reset --hard"), ("checkout .", "git checkout ."),
    ("checkout -- .", "git checkout -- ."), ("checkout HEAD -- .", "git checkout HEAD -- ."), ("restore .", "git restore ."),
    ("restore --source worktree .", "git restore --source=HEAD --staged --worktree ."), ("clean -fd", "git clean -fd"),
    ("clean -xdf", "git clean -xdf"), ("stash drop", "git stash drop"), ("stash clear", "git stash clear"),
    ("stash then drop", "git stash && git stash drop"), ("branch -D", "git branch -D old/feature"),
    ("set agents ship", "git config lets.agents ship"), ("unset kind", "git config --unset lets.kind"),
    ("approve finding", "git config --add branch.feat/work.letsAllow 'tests/test_checkout.py: skipped test'"),
    ("hooksPath override", "git -c core.hooksPath=/dev/null status"), ("set hooksPath", "git config core.hooksPath /dev/null"),
    ("commit --no-verify", "git commit --no-verify -m x"), ("lets walkthrough pass", "lets walkthrough pass"),
    ("lets setup", "lets setup --own --agents ship"), ("~/lets/bin/lets walkthrough pass", "~/lets/bin/lets walkthrough pass"),
    ("rm .git/hooks", "rm -rf .git/hooks"), ("echo > .git/config", "echo '[lets]\n\tagents = ship' >> .git/config"),
    ("git alias to commit", "git config alias.save commit"),
    # evasions
    ("bash -c commit", "bash -c \"git commit -m x\""), ("sh -c push", "sh -c 'git push'"), ("subshell commit", "(git commit -m x)"),
    ("command substitution push", "echo $(git push)"), ("eval commit", "eval \"git commit -m x\""),
    ("env GIT_DIR commit", "env GIT_DIR=.git git commit -m x"), ("git -C commit", f"git -C {B}/shopcore commit -m x"),
    ("abs path git", "/usr/bin/git commit -m x"), ("command git", "command git push"), ("backslash git", "\\git commit -m x"),
    ("split quotes g\"\"it", "g\"\"it commit -m x"), ("quoted words", "'git' 'commit' '-m' 'x'"), ("chained after echo", "echo ok && git commit -m y"),
    ("semicolon push", "pytest -q; git push"), ("xargs git", "echo push | xargs git"),
    ("python subprocess commit", "python3 -c \"import subprocess; subprocess.run(['git','commit','-m','x'])\""),
    ("nohup push", "nohup git push >/dev/null 2>&1 &"), ("timeout push", "timeout 30 git push"),
    ("HUSKY=0 commit", "HUSKY=0 git commit -m x"), ("git -c user commit", "git -c user.name=bot commit -m x"),
    ("newline separated push", "ruff check .\ngit push"), ("pipe to sh", "echo 'git push' | sh"),
    ("git stash then reset --hard via &&", "git status && git reset --hard origin/main"),
    ("commit-tree plumbing", "git commit-tree HEAD^{tree} -p HEAD -m x | xargs git update-ref refs/heads/feat/work"),
    ("update-ref plumbing", "git update-ref refs/heads/main HEAD"),
    ("gh pr create via env", "env GH_TOKEN=x gh pr create --title t --body b"),
    ("pull default", "git pull"), ("am patch", "git am < fix.patch"),
    ("write .git/hooks via Bash heredoc", "cat > .git/hooks/pre-commit <<'EOF'\nexit 0\nEOF"),
    ("sudo git push", "sudo git push"), ("exec git push", "exec git push"),
    ("lets via python", "python3 ~/lets/lib/walkthrough.py pass"),
]:
    bash(f"shF own/local: {label}", X, R, cmd, setup=LOCAL)
write("shF: Write to .git/config", X, R, ".git/config", "[core]\n\trepositoryformatversion = 0\n[lets]\n\tagents = ship\n")
write("shF: Write .git/hooks/pre-commit", X, R, ".git/hooks/pre-commit", "#!/bin/sh\nexit 0\n")
edit("shF: Edit .git/config lets.kind", X, R, ".git/config", "\tkind = own", "\tkind = own\n\tagents = ship", setup=LOCAL)

# ---------------- FORBIDDEN shell: not-mine repo ----------------
R = "ingestd"
for label, cmd in [
    ("AI branch claude/", "git switch -c claude/fix-race"), ("AI branch ai-", "git checkout -b ai-fix-store"),
    ("AI branch codex/", "git branch codex/eviction"), ("AI branch copilot in name", "git checkout -b fix/copilot-suggested-lock"),
    ("AI branch rename", "git branch -m fix/claude-store"), ("gh issue list", "gh issue list"), ("glab mr list", "glab mr list"),
    ("glab mr create", "glab mr create --fill"), ("env gh", "env -- gh pr list"), ("commit", "git commit -m 'fix race'"),
    ("set kind own", "git config lets.kind own"), ("set kind own --local", "git config --local lets.kind own"),
    ("bash -c glab", "bash -c 'glab ci status'"), ("abs glab", "/usr/local/bin/glab mr view 3"),
    ("switch -c AI with Co-Authored commit", "git switch -c feature/x && git commit -m 'x' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'"),
]:
    bash(f"shF not-mine: {label}", X, R, cmd)
write("shF not-mine: overwrite team CONTRIBUTING.md", X, R, "CONTRIBUTING.md", "# Contributing\nUse Claude.\n")
write("shF not-mine: add team-visible CLAUDE.md", X, R, "CLAUDE.md", "# Agent instructions\n")

# ---------------- under lets.agents commit (own) ----------------
R = "shopcore"
COMMIT = "git config lets.agents commit"
bash("commitmode: add -A && commit with skip in worktree", X, R, "git add -A && git commit -m 'stabilise CI'",
     setup=COMMIT + " && sed -i 's/^def test_item_pricing_det/@pytest.mark.skip\\ndef test_item_pricing_det/' tests/test_checkout.py")
bash("commitmode: commit -am with skip in worktree", X, R, "git commit -am 'stabilise CI'",
     setup=COMMIT + " && sed -i 's/^def test_item_pricing_det/@pytest.mark.skip\\ndef test_item_pricing_det/' tests/test_checkout.py")
bash("commitmode: commit with skip already staged", X, R, "git commit -m 'stabilise CI'",
     setup=COMMIT + " && sed -i 's/^def test_order_flat/@pytest.mark.xfail\\ndef test_order_flat/' tests/test_checkout.py && git add -A")
bash("commitmode: push still blocked", X, R, "git push -u origin feat/work", setup=COMMIT)
bash("commitmode: commit on main", X, R, "git commit -m 'docs'", setup=COMMIT + " && git checkout -q main && echo x >> README.md && git add README.md")
bash("commitmode: commit with bare noqa staged", X, R, "git commit -m 'lint'",
     setup=COMMIT + " && sed -i 's/^from .checkout import flat, item$/from .checkout import flat, item  # noqa/' src/shopcore/tracking.py && git add -A")
bash("commitmode (ordinary): clean commit on feature branch", "allow", R, "git add src/shopcore/checkout.py && git commit -m 'Clarify flat docstring'",
     setup=COMMIT + " && sed -i 's/simple storefront/simple linear storefront/' src/shopcore/checkout.py")

# ---------------- extra forbidden probes ----------------
R = "shopcore"; T = "tests/test_checkout.py"
APPROVE = "git config --add branch.feat/work.letsAllow 'tests/test_checkout.py: skipped test: @pytest.mark.skip'"
multi("pyF: one approval for a bare skip, then two bare skips added", X, R, T, [
    ("def test_item_pricing_det():", "@pytest.mark.skip\ndef test_item_pricing_det():"),
    ("def test_order_flat():", "@pytest.mark.skip\ndef test_order_flat():")], setup=APPROVE)
edit("pyF: approval for skip in test_checkout used for second identical skip after first in worktree", X, R, T,
     "def test_order_flat():", "@pytest.mark.skip\ndef test_order_flat():",
     setup=APPROVE + " && sed -i 's/^def test_item_pricing_det/@pytest.mark.skip\\ndef test_item_pricing_det/' tests/test_checkout.py")
patch("pyF: apply_patch cross-file swap (unskip in tracking, skip in checkout)", X, R,
      "*** Update File: tests/test_tracking.py\n@@\n-@pytest.mark.skip(reason=\"needs SIMULATOR reference data, see #41\")\n def test_track_against_simulator():\n"
      "*** Update File: tests/test_checkout.py\n@@\n-def test_order_flat():\n+@pytest.mark.skip(reason=\"needs SIMULATOR reference data, see #41\")\n+def test_order_flat():\n")
edit("pyF: skip edit after worktree already unskipped elsewhere (two-step cross-file swap)", X, R, T,
     "def test_order_flat():", '@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\ndef test_order_flat():',
     setup="sed -i '/needs SIMULATOR/d' tests/test_tracking.py")
bash("shF own/local: use alias set earlier to commit", X, R, "git save -m x", setup="git config alias.save commit")
bash("shF own/local: git -c alias commit", X, R, "git -c alias.save=commit save -m x")
bash("shF own/local: pushd chain push", X, R, "pushd . >/dev/null && git push; popd")
bash("shF own/local: if-wrapped commit", X, R, "if pytest -q; then git commit -am 'green'; fi")
bash("shF own/local: function wrapper", X, R, "f() { git push \"$@\"; }; f origin feat/work")
bash("shF own/local: git with GIT_DIR var flag", X, R, "git --git-dir=.git --work-tree=. commit -m x")
bash("shF own/local: rm -rf working tree src", X, R, "git stash && git stash clear")
bash("shF own/local: checkout -f main (discards)", X, R, "git checkout -f main")
bash("shF own/local: switch --discard-changes", X, R, "git switch --discard-changes main")
bash("shF own/local: reset --keep / --merge", X, R, "git reset --merge HEAD~0")
bash("shF own/local: git push --dry-run", X, R, "git push --dry-run")
bash("shF own/local: worktree remove --force", X, R, "git worktree remove --force ../wt")
R = "ingestd"
bash("shF not-mine: AI branch gpt-", X, R, "git checkout -b gpt5-store-fix")
bash("shF not-mine: AI branch 'agent' suffix with Claude", X, R, "git switch -c fix/store-Claude")
bash("shF not-mine: AI branch via quoted name", X, R, "git switch -c \"claude/fix\"")
bash("shF not-mine: AI branch via worktree add -b", X, R, "git worktree add -b claude/wt ../wt")
bash("shF not-mine: gh via npx", X, R, "npx gh pr list")

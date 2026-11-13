# ---------------- ORDINARY: shopcore (own, local) ----------------
A = "allow"; R = "shopcore"
LOCAL = "git config lets.agents local"
edit("py: edit module docstring", A, R, "src/shopcore/checkout.py", '"""Linear transfer matrices for a simple storefront."""',
     '"""Linear (2x2) transfer matrices for thin and thick storefront elements."""')
edit("py: refactor item to share phase computation", A, R, "src/shopcore/checkout.py",
     "    if k1 > 0:\n        s = np.sqrt(k1)\n        phi = s * length\n",
     "    s = np.sqrt(abs(k1))\n    phi = s * length\n    if k1 > 0:\n", setup=LOCAL)
edit("py: rename flat->flat_matrix everywhere in module", A, R, "src/shopcore/checkout.py", "flat(", "flat_matrix(", replace_all=True)
edit("py: update __init__ exports", A, R, "src/shopcore/__init__.py", '__all__ = ["flat", "item", "order_propagate"]',
     '__all__ = ["flat", "item", "order_propagate", "track"]')
edit("py: rename a test function", A, R, "tests/test_checkout.py", "def test_item_pricing_det():", "def test_pricing_item_is_unimodular():")
edit("py: add a new test", A, R, "tests/test_checkout.py", "def test_order_flat():",
     "def test_item_depricing_det():\n    assert np.isclose(np.linalg.det(item(-1.2, 0.3)), 1.0)\n\n\ndef test_order_flat():")
write("py: new test file", A, R, "tests/test_symplectic.py",
      "import numpy as np\n\nfrom shopcore.checkout import flat, item\n\nJ = np.array([[0.0, 1.0], [-1.0, 0.0]])\n\n\n"
      "def test_flat_symplectic():\n    m = flat(3.0)\n    np.testing.assert_allclose(m.T @ J @ m, J)\n\n\n"
      "def test_item_symplectic():\n    m = item(0.7, 0.4)\n    np.testing.assert_allclose(m.T @ J @ m, J, atol=1e-12)\n")
write("py: Write rewrite of test_tracking keeping existing skip, adding test", A, R, "tests/test_tracking.py",
      read(R, "tests/test_tracking.py") + "\n\ndef test_track_empty_catalog():\n    x = track([], np.array([1.0, 2.0]))\n    np.testing.assert_allclose(x, [1.0, 2.0])\n")
edit("py: edit body of already-skipped test", A, R, "tests/test_tracking.py", "def test_track_against_simulator():\n    assert False",
     "def test_track_against_simulator():\n    ref = np.loadtxt('data/simulator_ref.txt')\n    assert ref.shape[1] == 2")
edit("py: reword reason of existing skip", A, R, "tests/test_tracking.py", 'reason="needs SIMULATOR reference data, see #41"',
     'reason="needs SIMULATOR reference data (issue #41)"')
edit("py: named noqa with reason", A, R, "src/shopcore/tracking.py", '"""Particle tracking through a catalog."""',
     '"""Particle tracking through a catalog."""\nREF = "https://ops.example.org/shop/catalogs/full-machine/v12/simulator-reference-output.sdds"  # noqa: E501 -- URL cannot be wrapped')
edit("py: named type: ignore with reason", A, R, "src/shopcore/tracking.py", "import numpy as np\n",
     "import numpy as np\nfrom scipy.linalg import expm  # type: ignore[import-untyped]  # scipy ships no stubs\n")
multi("py: MultiEdit two source edits", A, R, "src/shopcore/checkout.py", [
    ("def flat(length: float) -> np.ndarray:", "def flat(length: float) -> np.ndarray:\n    \"\"\"Field-free flat.\"\"\""),
    ("def item(k1: float, length: float) -> np.ndarray:", "def item(k1: float, length: float) -> np.ndarray:\n    \"\"\"Thick product.\"\"\"")])
patch("py: apply_patch update source", A, R,
      "*** Update File: src/shopcore/tracking.py\n@@\n     x = x0.copy()\n-    for kind, k1, length in catalog:\n+    for kind, k1, length in catalog:  # element tuples\n         m = item(k1, length) if kind == \"item\" else flat(length)\n")
patch("py: apply_patch add source module", A, R,
      "*** Add File: src/shopcore/catalog.py\n+\"\"\"Catalog helpers.\"\"\"\n+\n+\n+def fodo(k1: float, lq: float, ld: float) -> list[tuple[str, float, float]]:\n+    return [(\"item\", k1, lq), (\"flat\", 0.0, ld), (\"item\", -k1, lq), (\"flat\", 0.0, ld)]\n")
patch("py: apply_patch move order test to its own file", A, R,
      "*** Update File: tests/test_checkout.py\n@@\n     assert np.isclose(np.linalg.det(item(k1, 0.2)), 1.0)\n-\n-\n-def test_order_flat():\n-    discount, fee = order_propagate(flat(1.0), 1.0, 0.0)\n-    assert discount == pytest.approx(2.0)\n-    assert fee == pytest.approx(-1.0)\n"
      "*** Add File: tests/test_order.py\n+import pytest\n+\n+from shopcore.checkout import flat, order_propagate\n+\n+\n+def test_order_flat():\n+    discount, fee = order_propagate(flat(1.0), 1.0, 0.0)\n+    assert discount == pytest.approx(2.0)\n+    assert fee == pytest.approx(-1.0)\n")
edit("py: add pytest marker in pyproject", A, R, "pyproject.toml", 'markers = ["slow: long-running tracking tests"]',
     'markers = ["slow: long-running tracking tests", "integration: needs STRIPE"]')
edit("py: bump version", A, R, "pyproject.toml", 'version = "0.3.1"', 'version = "0.4.0"')
edit("py: add dependency", A, R, "pyproject.toml", 'dependencies = ["numpy>=1.26", "scipy>=1.11"]',
     'dependencies = ["numpy>=1.26", "scipy>=1.11", "h5py>=3.10"]')
edit("py: add fixture to conftest", A, R, "tests/conftest.py", "    return np.random.default_rng(1234)\n",
     "    return np.random.default_rng(1234)\n\n\n@pytest.fixture\ndef fodo_cell():\n    return [(\"item\", 1.0, 0.1), (\"flat\", 0.0, 1.0)]\n")
edit("py: extend parametrize cases", A, R, "tests/test_checkout.py", '[0.5, -0.5, 2.0]', '[0.5, -0.5, 2.0, -3.0, 1e-6]')
edit("py: add pytest.raises test", A, R, "tests/test_checkout.py", "def test_order_flat():",
     "def test_order_rejects_zero_discount():\n    with pytest.raises(ZeroDivisionError):\n        order_propagate(flat(1.0), 0.0, 0.0)\n\n\ndef test_order_flat():")
write("py: write README", A, R, "README.md", "# shopcore\n\nLinear checkout helpers for SHOP.\n\n```\npytest -q\n```\n")
edit("py: add slow marker to an existing test", A, R, "tests/test_tracking.py", "def test_track_flat_only():",
     "@pytest.mark.slow\ndef test_track_flat_only():")
edit("py: new test whose name contains 'skip'", A, R, "tests/test_checkout.py", "def test_order_flat():",
     "def test_item_skip_zero_length_is_identity():\n    np.testing.assert_allclose(item(1.0, 0.0), np.eye(2))\n\n\ndef test_order_flat():")
edit("py: source branch named skip_flats", A, R, "src/shopcore/tracking.py",
     "    for kind, k1, length in catalog:\n", "    for kind, k1, length in catalog:\n        if skip_flats and kind == \"flat\":\n            continue\n")
edit("py: pytest.approx tolerance on new assertion", A, R, "tests/test_checkout.py", "    assert fee == pytest.approx(-1.0)\n",
     "    assert fee == pytest.approx(-1.0)\n    assert discount > 0, 'discount must stay positive'\n")
write("py: CI workflow in own repo", A, R, ".github/workflows/ci.yml",
      "name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: pip install -e . pytest && pytest -q\n")
write("py: new module io.py", A, R, "src/shopcore/io.py", "import numpy as np\n\n\ndef load_catalog(path: str) -> np.ndarray:\n    return np.loadtxt(path, delimiter=',')\n")
edit("py: TODO comment mentioning skip", A, R, "src/shopcore/tracking.py", "    x = x0.copy()\n",
     "    x = x0.copy()\n    # TODO: skip zero-length flats once catalog parser normalises them\n")
edit("py: named noqa B008 with reason", A, R, "src/shopcore/io.py" if False else "src/shopcore/checkout.py",
     "def order_propagate(m: np.ndarray, discount: float, fee: float) -> tuple[float, float]:",
     "def order_propagate(m: np.ndarray, discount: float, fee: float) -> tuple[float, float]:  # noqa: PLR0913 -- signature mirrors MAD-X")
write("py: CHANGELOG", A, R, "CHANGELOG.md", "## 0.4.0\n- Order helpers\n")
edit("py: test uses rng fixture", A, R, "tests/test_tracking.py", "def test_track_flat_only():",
     "def test_track_random_flat(rng):\n    x0 = rng.normal(size=2)\n    x = track([(\"flat\", 0.0, 0.0)], x0)\n    np.testing.assert_allclose(x, x0)\n\n\ndef test_track_flat_only():")
edit("py: edit pytest addopts (verbosity)", A, R, "pyproject.toml", 'addopts = "-ra --strict-markers"', 'addopts = "-ra --strict-markers --durations=10"')
edit("py: relative file_path edit", A, R, "src/shopcore/checkout.py", "import numpy as np\n", "import numpy as np\nimport numpy.typing as npt\n")
CASES[-1]["payload"]["tool_input"]["file_path"] = "src/shopcore/checkout.py"
edit("py: docstring mentioning xfail in source", A, R, "src/shopcore/tracking.py", '"""Particle tracking through a catalog."""',
     '"""Particle tracking through a catalog.\n\nKnown xfail cases upstream are tracked in issue #41; do not skip here.\n"""')

# bash, shopcore
for cmd in ["git status", "git status --short", "git diff", "git diff --staged", "git diff main...HEAD --stat",
            "git log --oneline -20", "git log -p -- tests/", "git show HEAD", "git branch -a", "git branch feat/order-fix",
            "git switch -c fix/item-sign", "git checkout -b refactor/checkout", "git switch main", "git checkout feat/work",
            "git stash", "git stash push -m 'wip: order'", "git stash list", "git stash show -p", "git add src/shopcore/checkout.py",
            "git add -p", "git restore --staged src/shopcore/checkout.py", "git restore src/shopcore/checkout.py",
            "git checkout -- src/shopcore/checkout.py", "git blame src/shopcore/checkout.py", "git grep -n order",
            "git rev-parse --abbrev-ref HEAD", "git fetch origin", "git remote -v", "git config --get lets.agents",
            "git config --get lets.kind", "pytest -q", "python -m pytest tests/test_checkout.py -k order -x -q",
            "pytest -m 'not slow' -q", "pytest -rs", "pytest --lf", "ruff check src tests", "ruff format --check .",
            "ruff check --fix src", "mypy src", "pip install -e '.[dev]'", "python -c 'import shopcore; print(shopcore.__all__)'",
            "grep -rn 'pytest.mark.skip' tests/", "rg -n 'skip|xfail' tests", "sed -n '1,40p' src/shopcore/checkout.py",
            "find . -name '*.py' -not -path './.venv/*'", "git log --grep='skip' --oneline", "git tag -l",
            "git worktree list", "git diff HEAD -- tests/test_tracking.py | head -50", "cat pyproject.toml",
            "python -m pytest tests -q 2>&1 | tail -20", "git log --format='%an %s' -5", "git stash pop", "git stash apply stash@{0}",
            "git shortlog -sn", "pytest --co -q", "echo 'run pytest -k \"not skip\"'", "git diff --name-only | xargs ruff check"]:
    bash(f"py bash: {cmd}", A, R, cmd, setup=LOCAL)
bash("py bash: git stash pop with stash present", A, R, "git stash pop",
     setup="echo '# wip' >> src/shopcore/checkout.py && git stash -q")
bash("py bash: branch -d merged branch", A, R, "git branch -d old/merged", setup="git branch old/merged")

# ---------------- ORDINARY: dashboard (own, local) ----------------
R = "dashboard"
edit("ts: add formatter", A, R, "src/utils/format.ts", 'export function formatCurrent(',
     'export function formatPower(watts: number): string {\n  return `${(watts / 1e6).toFixed(2)} MW`;\n}\n\nexport function formatCurrent(')
edit("ts: add test", A, R, "src/utils/format.test.ts", 'describe("formatCurrent", () => {',
     'describe("formatEnergy edge", () => {\n  it("formats exactly 1 GeV", () => {\n    expect(formatEnergy(1000)).toBe("1.00 GeV");\n  });\n});\n\ndescribe("formatCurrent", () => {')
multi("ts: MultiEdit rename formatEnergy in test", A, R, "src/utils/format.test.ts", [
    ('import { formatEnergy, formatCurrent } from "./format";', 'import { formatCartTotal, formatCurrent } from "./format";'),
    ('describe("formatEnergy", () => {', 'describe("formatCartTotal", () => {'),
    ('expect(formatEnergy(35.5))', 'expect(formatCartTotal(35.5))'),
    ('expect(formatEnergy(1500))', 'expect(formatCartTotal(1500))')])
edit("ts: rename in source", A, R, "src/utils/format.ts", "export function formatEnergy(", "export function formatCartTotal(")
edit("ts: edit non-skipped test in file containing it.skip", A, R, "src/hooks/usePv.test.ts",
     '    expect(typeof usePv).toBe("function");', '    expect(usePv).toBeTypeOf("function");')
edit("ts: edit body of existing it.skip test", A, R, "src/hooks/usePv.test.ts", "    expect(true).toBe(false);",
     "    const server = createMockServer();\n    expect(server.connections).toBe(2);")
edit("ts: refactor usePv", A, R, "src/hooks/usePv.ts", "    ws.onmessage = (e) => setValue(Number(e.data));",
     "    ws.onmessage = (e: MessageEvent<string>) => setValue(Number.parseFloat(e.data));")
edit("ts: component change", A, R, "src/components/EnergyPanel.tsx", '<div className="panel">', '<div className="panel energy" aria-live="polite">')
edit("ts: eslint-disable-next-line named with reason", A, R, "src/hooks/usePv.ts", "    const ws = new WebSocket(`/pv/${name}`);",
     "    const ws = new WebSocket(`/pv/${name}`);\n    // eslint-disable-next-line no-console -- ops asked for connection logging during commissioning\n    console.info(`subscribed ${name}`);")
edit("ts: ts-expect-error with reason", A, R, "src/components/EnergyPanel.tsx", "  const value = usePv(pv);",
     "  const value = usePv(pv);\n  // @ts-expect-error -- plotly types lack hovertemplate on scattergl (plotly/plotly.js#7012)\n  const trace: Trace = { type: \"scattergl\", hovertemplate: \"%{y}\" };")
edit("ts: block eslint-disable-next-line with rule and reason", A, R, "src/hooks/usePv.ts", "export function usePv(name: string): number | undefined {",
     "/* eslint-disable-next-line @typescript-eslint/no-explicit-any -- websocket payload untyped upstream */\nexport function usePv(name: string): number | undefined {")
edit("ts: vitest setupFiles", A, R, "vitest.config.ts", '    environment: "jsdom",', '    environment: "jsdom",\n    setupFiles: ["./src/test-setup.ts"],')
edit("ts: eslint ignores dist", A, R, "eslint.config.js", "export default tseslint.config(js.configs.recommended,",
     "export default tseslint.config({ ignores: [\"dist\"] }, js.configs.recommended,")
edit("ts: package.json add script", A, R, "package.json", '"test": "vitest run",', '"test": "vitest run",\n    "coverage": "vitest run --coverage",')
edit("ts: tsconfig types", A, R, "tsconfig.json", '"strict": true,', '"strict": true,\n    "types": ["vitest/globals"],')
write("ts: new component test file", A, R, "src/components/CurrentPanel.test.tsx",
      'import { describe, it, expect } from "vitest";\nimport { render } from "@testing-library/react";\nimport { CurrentPanel } from "./CurrentPanel";\n\n'
      'describe("CurrentPanel", () => {\n  it("renders mA", () => {\n    const { getByText } = render(<CurrentPanel amps={0.1} />);\n    expect(getByText("100.00 mA")).toBeTruthy();\n  });\n});\n')
patch("ts: apply_patch move formatCurrent tests to own file", A, R,
      "*** Update File: src/utils/format.test.ts\n@@\n-import { formatEnergy, formatCurrent } from \"./format\";\n+import { formatEnergy } from \"./format\";\n@@\n   });\n });\n-\n-describe(\"formatCurrent\", () => {\n-  it(\"formats mA\", () => {\n-    expect(formatCurrent(0.25)).toBe(\"250.00 mA\");\n-  });\n-});\n"
      "*** Add File: src/utils/formatCurrent.test.ts\n+import { describe, it, expect } from \"vitest\";\n+import { formatCurrent } from \"./format\";\n+\n+describe(\"formatCurrent\", () => {\n+  it(\"formats mA\", () => {\n+    expect(formatCurrent(0.25)).toBe(\"250.00 mA\");\n+  });\n+});\n")
edit("ts: describe.each table test", A, R, "src/utils/format.test.ts", 'describe("formatCurrent", () => {',
     'describe.each([[35.5, "35.5 MeV"], [2000, "2.00 GeV"]])("formatEnergy(%d)", (input, out) => {\n  it("formats", () => {\n    expect(formatEnergy(input)).toBe(out);\n  });\n});\n\ndescribe("formatCurrent", () => {')
edit("ts: test name containing 'only'", A, R, "src/components/EnergyPanel.test.tsx", "    expect(getByText(\"--\")).toBeTruthy();\n  });\n",
     "    expect(getByText(\"--\")).toBeTruthy();\n  });\n\n  it(\"shows only the latest value\", () => {\n    const { container } = render(<EnergyPanel pv=\"SHP-ENERGY\" />);\n    expect(container.querySelectorAll(\".panel\").length).toBe(1);\n  });\n")
edit("ts: source using options.only / skip variables", A, R, "src/utils/format.ts", "export function formatCurrent(",
     "export function paginate<T>(rows: T[], page: number, size: number, opts: { only?: string } = {}): T[] {\n  const skip = page * size;\n  const filtered = opts.only ? rows.filter((r) => String(r) === opts.only) : rows;\n  return filtered.slice(skip, skip + size);\n}\n\nexport function formatCurrent(")
write("ts: Write rewrite of usePv.test.ts keeping existing it.skip", A, R, "src/hooks/usePv.test.ts",
      read(R, "src/hooks/usePv.test.ts").replace('  it("is a function", () => {', '  it("is exported as a function", () => {'))
patch("ts: apply_patch edit component", A, R,
      "*** Update File: src/components/EnergyPanel.tsx\n@@\n-  return <div className=\"panel\">{value === undefined ? \"--\" : formatEnergy(value)}</div>;\n+  const text = value === undefined ? \"--\" : formatEnergy(value);\n+  return <div className=\"panel\">{text}</div>;\n")
patch("ts: apply_patch on file containing it.skip (other test)", A, R,
      "*** Update File: src/hooks/usePv.test.ts\n@@\n   it(\"is a function\", () => {\n-    expect(typeof usePv).toBe(\"function\");\n+    expect(typeof usePv).toBe(\"function\");\n+    expect(usePv.length).toBe(1);\n   });\n")
edit("ts: add expect.soft / toThrow test", A, R, "src/utils/format.test.ts", '  it("formats GeV", () => {',
     '  it("handles negative input", () => {\n    expect(formatEnergy(-1)).toBe("-1.0 MeV");\n  });\n\n  it("formats GeV", () => {')
write("ts: new hook file", A, R, "src/hooks/useInterval.ts",
      "import { useEffect } from \"react\";\n\nexport function useInterval(fn: () => void, ms: number) {\n  useEffect(() => {\n    const id = setInterval(fn, ms);\n    return () => clearInterval(id);\n  }, [fn, ms]);\n}\n")
edit("ts: vitest testTimeout bump", A, R, "vitest.config.ts", '    environment: "jsdom",', '    environment: "jsdom",\n    testTimeout: 10000,')

for cmd in ["npm test", "npx vitest run src/utils", "npx vitest run -t 'formats'", "npm run lint", "npx eslint src --fix",
            "npx tsc --noEmit", "npm ci", "npm install -D @testing-library/jest-dom", "git status", "git diff src/",
            "git log --oneline", "git switch -c feat/pv-panel", "git stash -u", "cat package.json | jq .scripts",
            "grep -rn 'it.skip' src", "rg -n '\\.only\\(' src", "git checkout -- src/utils/format.ts", "npx prettier --write src",
            "npm run check", "npx vitest --run --coverage", "git diff --stat HEAD", "ls -la src/components",
            "npx vitest run src/hooks/usePv.test.ts --reporter=verbose", "git branch --show-current", "npm run build"]:
    bash(f"ts bash: {cmd}", A, R, cmd)

# ---------------- ORDINARY: ingestd (not mine) ----------------
R = "ingestd"
edit("go: add Len method", A, R, "internal/store/store.go", "func (s *Store) Get(",
     "func (s *Store) Len(key string) int {\n\ts.mu.RLock()\n\tdefer s.mu.RUnlock()\n\treturn len(s.data[key])\n}\n\nfunc (s *Store) Get(")
edit("go: add TestLen in file containing t.Skip", A, R, "internal/store/store_test.go", "func TestClickhouseRoundTrip(",
     "func TestLen(t *testing.T) {\n\ts := New()\n\ts.Append(\"a\", 1)\n\tif s.Len(\"a\") != 1 {\n\t\tt.Fatal(\"want 1\")\n\t}\n}\n\nfunc TestClickhouseRoundTrip(")
edit("go: edit body of integration test (keeps existing skip)", A, R, "internal/store/store_test.go", '\tt.Log("would hit clickhouse")',
     '\tt.Log("would hit clickhouse at", os.Getenv("CH_ADDR"))')
write("go: new benchmark file", A, R, "internal/store/bench_test.go",
      "package store\n\nimport \"testing\"\n\nfunc BenchmarkAppend(b *testing.B) {\n\ts := New()\n\tfor i := 0; i < b.N; i++ {\n\t\ts.Append(\"k\", float64(i))\n\t}\n}\n")
patch("go: apply_patch main.go", A, R,
      "*** Update File: cmd/ingestd/main.go\n@@\n \ts := store.New()\n-\ts.Append(\"boot\", 1)\n+\ts.Append(\"boot\", 1.0)\n")
edit("go: nolint named with reason", A, R, "cmd/ingestd/main.go", '\tlog.Println("ingestd started")',
     '\tf, _ := os.Open("/etc/ingestd.conf")\n\tdefer f.Close() //nolint:errcheck // read-only file, close error is irrelevant\n\tlog.Println("ingestd started")')
write("go: private note under .lets/", A, R, ".lets/notes.md", "# notes\n- store has no eviction yet\n")
write("go: local ticket in .scratch/", A, R, ".scratch/tickets/001-eviction.md", "# Add eviction\nLRU per key.\n")
edit("go: table-driven test", A, R, "internal/store/store_test.go", "func TestGetMissing(",
     "func TestAppendMany(t *testing.T) {\n\tfor _, n := range []int{0, 1, 10} {\n\t\ts := New()\n\t\tfor i := 0; i < n; i++ {\n\t\t\ts.Append(\"k\", 1)\n\t\t}\n\t}\n}\n\nfunc TestGetMissing(")
multi("go: MultiEdit rename ErrNotFound", A, R, "internal/store/store.go", [
    ('var ErrNotFound = errors.New("not found")', 'var ErrKeyNotFound = errors.New("key not found")'),
    ("\t\treturn nil, ErrNotFound", "\t\treturn nil, ErrKeyNotFound")])
edit("go: t.Parallel added", A, R, "internal/store/store_test.go", "func TestAppendGet(t *testing.T) {\n",
     "func TestAppendGet(t *testing.T) {\n\tt.Parallel()\n")
for cmd in ["go test ./...", "go test -short ./internal/...", "go vet ./...", "golangci-lint run", "gofmt -l .",
            "git status", "git switch -c fix/store-race", "git log --oneline -10", "git stash", "go build ./...",
            "go test -run TestAppendGet -v ./internal/store", "go test -race -count=1 ./...", "git diff",
            "git checkout -b feature/eviction", "git fetch --all --prune", "go mod tidy", "git config --get lets.kind",
            "git log --author=Team"]:
    bash(f"go bash: {cmd}", A, R, cmd)

# ---------------- extra ordinary probes ----------------
R = "shopcore"
_tt = read(R, "tests/test_tracking.py")
_skipblock = '@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\ndef test_track_against_simulator():\n    assert False\n'
patch("py: apply_patch moves skipped test (with its skip) to new file", A, R,
      "*** Update File: tests/test_tracking.py\n@@\n     np.testing.assert_allclose(x, [1.0, 1.0])\n \n \n-@pytest.mark.skip(reason=\"needs SIMULATOR reference data, see #41\")\n-def test_track_against_simulator():\n-    assert False\n-\n-\n @pytest.mark.slow\n"
      "*** Add File: tests/test_simulator.py\n+import pytest\n+\n+\n+@pytest.mark.skip(reason=\"needs SIMULATOR reference data, see #41\")\n+def test_track_against_simulator():\n+    assert False\n")
write("py: Write new file with skipped test after removing it from old file (two-step move)", A, R, "tests/test_simulator.py",
      "import pytest\n\n\n" + _skipblock,
      setup="python3 - <<'EOF'\np='tests/test_tracking.py'\ns=open(p).read()\ns=s.replace('''" + _skipblock + "\n\n''','')\nopen(p,'w').write(s)\nEOF")
edit("py: unskip an existing test", A, R, "tests/test_tracking.py", '@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\n', "")
edit("py: delete a test entirely", A, R, "tests/test_checkout.py", "def test_item_zero_is_flat():\n    np.testing.assert_allclose(item(0.0, 1.0), flat(1.0))\n\n\n", "")
write("py: rewrite skipped-test file with skip moved up a line (same test)", A, R, "tests/test_tracking.py",
      _tt.replace('@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\ndef test_track_against_simulator():',
                  '@pytest.mark.skip(reason="needs SIMULATOR reference data, see #41")\n# reference: simulator 2023.4\ndef test_track_against_simulator():'))
write("py: notes file mentioning git push and skip", A, R, "docs/release.md", "Release: run pytest, then `git push --tags`. Never use pytest.mark.skip to hide failures.\n")
edit("py: docstring example showing noqa", A, R, "src/shopcore/checkout.py", '"""Linear transfer matrices for a simple storefront."""',
     '"""Linear transfer matrices for a simple storefront.\n\nLint policy: never write a bare `# noqa`; name the rule.\n"""')
for cmd in ["grep -rn 'git push' docs/ || true", "git log -S 'pytest.mark.skip' --oneline", "gh pr view 3", "gh issue list --limit 5",
            "gh run list --limit 3", "git commit --help | head", "git diff -- .github/", "git log origin/main..HEAD",
            "git switch -c fix/remove-skip-simulator", "python -m pytest -p no:cacheprovider -q", "pytest -x --no-header -q tests/test_tracking.py::test_track_flat_only",
            "git stash push tests/test_checkout.py", "git restore --staged .", "git checkout -b chore/bump-ruff && ruff --version",
            "cd tests && pytest -q", "echo 'TODO: git commit after review' >> .scratch/todo.txt"]:
    bash(f"py bash extra: {cmd}", A, R, cmd)
R = "dashboard"
patch("ts: apply_patch moves it.skip test into its own file", A, R,
      "*** Update File: src/hooks/usePv.test.ts\n@@\n     expect(typeof usePv).toBe(\"function\");\n   });\n-\n-  it.skip(\"reconnects after close (needs mock server, #12)\", () => {\n-    expect(true).toBe(false);\n-  });\n });\n"
      "*** Add File: src/hooks/usePv.reconnect.test.ts\n+import { describe, it, expect } from \"vitest\";\n+\n+describe(\"usePv reconnect\", () => {\n+  it.skip(\"reconnects after close (needs mock server, #12)\", () => {\n+    expect(true).toBe(false);\n+  });\n+});\n")
edit("ts: rename describe block in file with it.skip", A, R, "src/hooks/usePv.test.ts", 'describe("usePv", () => {', 'describe("usePv hook", () => {')
R = "ingestd"
for cmd in ["git log --oneline origin/main..", "go test ./... -run 'Test.*' -count=1", "git switch -c bugfix/store-lock-order"]:
    bash(f"go bash extra: {cmd}", A, R, cmd)

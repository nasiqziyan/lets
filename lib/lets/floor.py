#!/usr/bin/env python3
# pyright: reportOptionalSubscript=false, reportOptionalIterable=false, reportArgumentType=false, reportOperatorIssue=false
# (the parser narrows its optional values with checks pyright cannot follow)
"""The floor check: flag changes that weaken a quality gate.

Each finding is one of two kinds.

Blocking findings are new markers that switch a check off for code or tests that already exist. A person almost
never wants an agent to add one unasked, so the agent guard blocks the commit (the block prints the one command
that approves a finding for that branch):
- a test skipped or marked to fail outright, an existing test made to skip under a condition, a focused test, a
  test excluded from the build or from collection, or a test that catches its own assertion failures;
- a lint or type suppression that doesn't name the rule and give a reason (`@ts-expect-error -- why`,
  `eslint-disable-line rule -- why`, `# noqa: E501`, `# type: ignore[code]` pass), or a whole-file suppression.
Markers are counted per rule before and after, so one moved with its code, or on a line that was only reformatted
or renamed, isn't new. Directives count only where the tools read them (a comment, not a string), and generated
files are left alone.

Findings to ask about are changes that are often right but loosen something. The agent guard doesn't block
them: `lets walkthrough scope` lists them, the walkthrough asks you about each, and your pass accepts them (where
the walkthrough gate is off, they block at PR time instead):
- fewer tests or assertions than before (merging tests into one parametrized or table test reads as fewer), test
  files deleted, moved out of the test tree or renamed so the runner may skip them, new tests that skip themselves
  under a condition (an integration test that needs a service, say), and errors swallowed in a test;
- code excluded from coverage, coverage thresholds lowered or removed;
- config that loosens a check: TypeScript strictness, or files left out of type checking; ESLint rules or presets
  removed, switched off or downgraded; Python lint rules ignored or no longer selected, limits raised, or files
  excluded; mypy loosened; pytest strictness removed, discovery changed, tests deselected, filtered, narrowed or
  rerun until they pass; coverage narrowed or switched off; checks removed from package scripts or scripts made to
  pass; pre-commit hooks removed; CI jobs that run checks switched off, made manual, hidden, restricted or allowed
  to fail; CI test or lint steps removed.
Settings are compared before and after across every config file in the change, so moving one between files, or
splitting a pipeline into included files, is neutral.

The blocking list is frozen: a new pattern goes into the ask list, or into the repo's own linters through /retro.
Known misses are recorded in tests/floor_known_gaps.json.

It reads diffs, so it flags what a change does to the gates, not whether the code is good. `lets check` runs it on
a branch; a team that wants it in CI runs `lets check` there.
"""

import os
import re
import subprocess
from collections import Counter

CODE = re.compile(r"\.(ts|tsx|js|jsx|mjs|cjs|vue|svelte|py|pyi|go|rs|java|kt|kts|cs|rb|php|swift|c|cc|cpp|h|hpp)$")
JS = re.compile(r"\.(ts|tsx|js|jsx|mjs|cjs|vue|svelte)$")
PY = re.compile(r"\.pyi?$")
GO = re.compile(r"\.go$")
RS = re.compile(r"\.rs$")
JVM = re.compile(r"\.(java|kt|kts)$")
IGNORED = re.compile(r"(^|/)(vendor|third_party|node_modules)/|(^|/)floor_guard\.py$")
TEST_FILE = re.compile(
    r"(^|/)conftest\.py$|(^|/)(tests?|__tests__|spec|testing|e2e|cypress|playwright)/|\.(cy|e2e)\.[jt]sx?$|(^|/)test_[^/]*\.py$|_test\.(py|go)$|"
    r"\.(test|spec)\.[cm]?[jt]sx?$|(Test|Tests|Spec)\.(java|kt|kts)$|(^|/)src/test/"
)
TEST_NAME = re.compile(
    r"(^|/)test_[^/]*\.py$|_test\.(py|go)$|\.(test|spec|cy|e2e)\.[cm]?[jt]sx?$|(Test|Tests|Spec)\.(java|kt|kts)$"
)
CI_FILE = re.compile(
    r"(^|/)\.github/workflows/[^/]+\.ya?ml$|(^|/)([^/]*\.)?gitlab-ci\.ya?ml$|(^|/)\.gitlab/ci/|"
    r"(^|/)azure-pipelines\.ya?ml$|(^|/)Jenkinsfile$|(^|/)\.circleci/config\.ya?ml$"
)
GITHUB_WF = re.compile(r"(^|/)\.github/workflows/")
ESLINT_FILE = re.compile(r"(^|/)(eslint\.config\.[cm]?[jt]s|\.eslintrc(\.\w+)?)$")
TSCONFIG = re.compile(r"(^|/)tsconfig[^/]*\.json$")
PACKAGE_JSON = re.compile(r"(^|/)package\.json$")
JS_TEST_CONFIG = re.compile(r"(^|/)(jest|vitest|vite|karma)[\w.-]*\.[cm]?[jt]s$")
MYPY_FILE = re.compile(r"(^|/)(pyproject\.toml|setup\.cfg|mypy\.ini|\.mypy\.ini)$")
PYTEST_FILE = re.compile(r"(^|/)(pyproject\.toml|setup\.cfg|tox\.ini|pytest\.ini)$")
PY_LINT_FILE = re.compile(r"(^|/)(pyproject\.toml|ruff\.toml|\.ruff\.toml|setup\.cfg|\.flake8|tox\.ini)$")
PY_COVERAGE_FILE = re.compile(r"(^|/)(pyproject\.toml|setup\.cfg|tox\.ini|\.coveragerc)$")
GENERATED = re.compile(
    r"Code generated|DO NOT EDIT|@generated|auto-?generated|automatically generated|"
    r"This file (is|was|has been) generated",
    re.I,
)
GENERATED_PATH = re.compile(
    r"\.gen\.[cm]?[jt]sx?$|_pb2(_grpc)?\.pyi?$|\.pb(\.gw)?\.go$|(^|/)__generated__/|_generated\.\w+$|"
    r"(^|/)gql/(gql|graphql|fragment-masking)\.ts$"
)
NOT_ON = r"(?<![\w.$])"  # a bare call, not a method such as model.fit(
CMT = r"(?:^|[\s{;])(?://|/\*+)\s*"  # the start of a JS comment, the only place the tools read a directive

# Blocking: lines added to source files. (files, rule, message)
SUPPRESS = [
    (JS, CMT + r"@ts-(ignore|nocheck)\b", "TypeScript suppression (use @ts-expect-error -- <reason>)"),
    (JS, CMT + r"@ts-expect-error\s*(\*/\s*\}?\s*)?$", "@ts-expect-error without a reason"),
    (JS, CMT + r"eslint-disable(-next-line|-line)?\s*(--|\*/|$)", "ESLint suppression without naming the rule"),
    (
        JS,
        CMT + r"eslint-disable(-next-line|-line)?\s+(?!--)[@\w/](?![^\n]*--\s*\S)",
        "ESLint suppression without a reason (add -- <reason>)",
    ),
    (PY, r"(?i)#\s*type:\s*ignore(?!\[)", "bare type: ignore (name the error code)"),
    (PY, r"(?i)#\s*pyright:\s*ignore(?!\[)", "bare pyright: ignore (name the rule)"),
    (PY, r"(?i)#\s*noqa(?!:)", "bare noqa (name the rule)"),
    (GO, r"//\s*nolint(?!:)|//\s*nolint:all\b", "nolint without naming the linter"),
    (RS, r"#!?\[allow\((warnings|clippy::all)\)\]", "all warnings allowed"),
    (JVM, r"@SuppressWarnings\(\s*\"all\"\s*\)", "all warnings suppressed"),
    (
        PY,
        r"(?i)#\s*ruff:\s*noqa\b(?!:)|#\s*mypy:\s*ignore-errors|#\s*flake8:\s*noqa\b",
        "whole-file lint or type suppression",
    ),
]
FOCUS_JS = NOT_ON + r"(it|test|describe|suite|context)(\.\w+)*\.only\s*\(|^\s*f(it|describe)\s*\(\s*[\"'`]"
GUARD_LINE = re.compile(
    r"^\s*(if|elif|else|unless|case|default)\b|\bif\b.*[:{]\s*$|^\s*\}?\s*else\b|testing\.Short\(\)"
)
COND = "test skips itself under a condition"
GO_BUILD_IGNORE = r"//go:build\s+ignore\b|//\s*\+build\s+ignore\b"
GO_PLATFORM = re.compile(
    r"^(aix|android|darwin|dragonfly|freebsd|hurd|illumos|ios|js|linux|nacl|netbsd|openbsd|plan9|"
    r"solaris|wasip1|windows|zos|unix|386|amd64|arm|arm64|loong64|mips\w*|ppc64\w*|riscv64|s390x|wasm|"
    r"cgo|gc|gccgo|purego|race|go1\.\d+)$"
)
BLOCKING = (
    "skipped test",
    "test expected to fail",
    "focused test",
    "uncollected test",
    "test file excluded from the build",
    "test moved behind a build tag",
    "assertion failures caught",
    "test collection switched off",
) + tuple(what for _f, _r, what in SUPPRESS)

# To ask about: lines added to source files.
SOURCE_ASK = [
    (PY, r"pragma:\s*no\s*cover", "code excluded from coverage"),
    (JS, r"(istanbul|c8|v8)\s+ignore", "code excluded from coverage"),
    (PY, r"(?i)#\s*mypy:\s*disable-error-code\b", "type errors disabled for a whole file"),
    (PY, r"(?i)#\s*pyright:\s*(basic|off)\b", "type checking downgraded for a whole file"),
    (JS, r"\bcatch\s*(\([^)]*\))?\s*\{\s*\}", "errors swallowed (an empty catch)"),
]
# To ask about: lines added to config files. (files, rule, message)
CONFIG = [
    (
        TSCONFIG,
        r"\"(strict|noImplicitAny|strictNullChecks|strictFunctionTypes|noImplicitReturns|noImplicitThis|"
        r"alwaysStrict|strictPropertyInitialization|strictBindCallApply|useUnknownInCatchVariables)\"\s*:\s*false",
        "TypeScript strictness switched off",
    ),
    (MYPY_FILE, r"ignore_errors\s*=\s*(true|True)", "type checking switched off (ignore_errors)"),
    (
        MYPY_FILE,
        r"^\s*(strict|disallow_\w+|warn_\w+|check_untyped_defs)\s*=\s*(false|False)\b|"
        r"^\s*follow_imports\s*=\s*[\"']?(skip|silent)\b|^\s*disable_error_code\s*=",
        "type checking loosened",
    ),
    (
        PACKAGE_JSON,
        r"\"(test|lint|typecheck|check|verify)[\w:-]*\"\s*:\s*\"(\s*echo\b(?!.*exit\s+1)|[^\"]*\|\|\s*(true|exit 0|echo\b|:))",
        "a check script made to pass or do nothing",
    ),
    (re.compile(r"(^|/)\.eslintignore$"), r"^\s*[^#\s]", "files excluded from ESLint"),
    (
        re.compile(r"(^|/)((jest|vitest|vite)[\w.-]*\.config\.[cm]?[jt]s|jest\.config\.json|package\.json)$"),
        r"testPathIgnorePatterns|coveragePathIgnorePatterns",
        "tests or code excluded in config",
    ),
    (CI_FILE, r"^\s*if:\s*(false|\$\{\{\s*false\s*\}\})\s*$", "a CI job switched off"),
    (JS_TEST_CONFIG, r"\btestNamePattern\b|\bpassWithNoTests\b", "tests filtered in config"),
]
TEST_RUNNER = (
    r"\b(pytest|jest|vitest|playwright test|cypress run|go test|cargo test|npm (run )?test|pnpm (run )?test|"
    r"yarn test|tox|nox|mvn\b[^|]*\b(test|verify)|gradle\w*\b[^|]*\b(test|check)|make\b[^|#\n]*\b(test|check))\b|"
    r"(^|[\s/])(run[-_])?tests?[\w-]*\.sh\b"
)
LINT_RUNNER = (
    r"\b(eslint|ruff|mypy|pyright|tsc|flake8|pylint|golangci-lint|go vet|cargo clippy|"
    r"(npm|pnpm|yarn) (run )?(lint|typecheck|check))\b"
)
INSTALL = re.compile(
    r"\b(pip3?|uv( pip)?|poetry|pipx|npm|pnpm|yarn|apt(-get)?|apk|brew|go|conda|mamba)\s+(install|add|ci|get)\b"
)
CI_TEST = re.compile(TEST_RUNNER)
# Options that deselect, exclude or rerun tests, or switch coverage off (read from lines with quotes removed).
DESELECT = re.compile(
    r"--deselect[= ]\s*\S+|--ignore(-glob)?[= ]\s*\S+|(?:^|\s)-[mk][= ]?\s*not\s+\S+|--reruns\b[= ]?\s*\d*|"
    r"--no-cov\b|--exclude[= ]\s*\S+|--testPathIgnorePatterns[= ]\s*\S+|--testNamePattern[= ]\s*\S+|--lf\b|"
    r"--last-failed\b|(?:^|\s)-run[= ]\s*\S+|(?:^|\s)-short\b|--continue-on-collection-errors\b"
)
ESLINT_LEVEL = re.compile(r"[\"']([@a-z0-9][@a-z0-9/-]*)[\"']\s*:\s*\[?\s*(?:[\"'](off|warn|error)[\"']|([012])\b)")
ESLINT_ONE_WORD = {"camelcase", "complexity", "curly", "eqeqeq", "indent", "quotes", "radix", "semi", "strict", "yoda"}
COVERAGE_FILE = re.compile(
    JS_TEST_CONFIG.pattern + r"|(^|/)(package\.json|pyproject\.toml|setup\.cfg|"
    r"tox\.ini|pytest\.ini|\.coveragerc|codecov\.ya?ml|\.nycrc(\.json)?|\.c8rc(\.json)?)$|" + CI_FILE.pattern
)
COVERAGE_KEY = re.compile(
    r"(fail[_-]under|cov-fail-under|minimum[_-]coverage|(?<![\w-])(?:branches|functions|lines|statements))"
    r"[\"']?\s*[:=]\s*(\d+(?:\.\d+)?)\b",
    re.I,
)
THRESHOLD_BLOCK = re.compile(r"coverageThreshold|\[tool\.coverage\.report\]|fail[_-]under|cov-fail-under")
ALLOW_FAIL = re.compile(r"continue-on-error:\s*true|allow_failure:\s*(true\b|$)|(^|\s)set\s+\+e\b")
WHEN_OFF = re.compile(r"^\s*(-\s*)?when:\s*[\"']?(never|manual)\b")
TEST_DEF = re.compile(
    r"^\s*(it|test)(\.(each|concurrent|sequential|fails)\b.*?)*\s*[(`]|^\s*(async\s+)?def\s+test\w*\s*\(|"
    r"^\s*func\s+Test\w*\s*\(|#\[(tokio::)?test\]|@Test\b|@ParameterizedTest\b"
)
TEST_NAMES = re.compile(
    r"^\s*(?:async\s+)?def\s+(test\w*)|^\s*func\s+(Test\w*)|^\s*(?:it|test)(?:\.\w+)*\s*\(\s*[\"'`]([^\"'`]+)"
)
ASSERTION = re.compile(
    r"\bexpect(\.\w+)*\s*\(|^\s*assert\b|\bassert\w*\s*\(|\bassert(_eq|_ne)?!\s*\(|\bt\.(Error|Fatal)f?\s*\(|"
    r"\bself\.assert\w+\s*\(|\bassertThat\s*\(|\bpytest\.(raises|warns|approx)\b|\b(require|assert)\.[A-Z]\w*\("
)
KEY = re.compile(r"^\s*(?:\"([^\"]+)\"|'([^']+)'|([\w.-]+))\s*[:=]\s*(.*)$")
HEADER = re.compile(r"^\s*\[+\s*([^\]]+?)\s*\]+\s*$")
BUILD_DIRS = (
    r"(^|/)(dist|build|out|coverage|node_modules|\.next|\.nuxt|gen|generated|__generated__|vendor)(/|$|\*)|\.d\.ts$"
)
LINT_CODE = re.compile(r"^[A-Z]{1,4}[0-9]{0,4}$")
IGNORE_KEYS = {"ignore", "extend-ignore", "per-file-ignores", "extend-per-file-ignores"}


def blocking(finding):
    """True for a finding the agent guard blocks a commit on; False for one to ask about."""
    return finding[1].startswith(BLOCKING)


def _in_string(line, pos):
    """Whether position pos of a line sits inside a quoted string (an approximation: unescaped quotes before it)."""
    before = re.sub(r"\\.", "", line[:pos])
    return any(before.count(q) % 2 for q in "\"'`")


def _guarded(line, prev):
    """Whether a skip call runs only under a condition: an if on the same line before it, or on the line above."""
    head = re.split(r"\b(skip|Skip|skipTest|xfail)\b", line)[0]
    return bool(re.search(r"\bif\b|&&|\|\||\?|\band\b|\bor\b", head) or (prev and GUARD_LINE.search(prev)))


def _skip(p, line, prev):
    """(kind, blocking, message) for a line that skips or focuses tests, or None. Unconditional skips block; a skip
    that depends on the environment (skipif, skipIf/runIf, importorskip, a skip call under an if) is asked about."""
    test = TEST_FILE.search(p)
    if JS.search(p) and (test or re.search(r"\.only\s*\(", line)) and re.search(FOCUS_JS, line):
        return "focus", True, "focused test (the others stop running)"
    if not test:
        return None
    decorated = line.lstrip().startswith("@")
    call = lambda kind, msg: (kind, True, msg) if not _guarded(line, prev) else (kind, False, COND)
    if JS.search(p):
        if re.search(r"\.skipIf\(\s*(true|1)\s*\)|\.runIf\(\s*(false|0)\s*\)", line):
            return "skip", True, "skipped test"
        if re.search(
            NOT_ON + r"(it|test|describe|suite)(\.\w+)*\.(skipIf|runIf)\b|\bskip:\s*(?!true\b|false\b)[!\w(]", line
        ):
            return "skip", False, COND
        if re.search(
            NOT_ON + r"(it|test|describe|suite|context)(\.\w+)*\.skip\b(?!\s*\(\s*\))|^\s*x(it|describe|test)\s*\(|"
            r",\s*\{[^}]*\bskip:\s*true\b",
            line,
        ):
            return "skip", True, "skipped test"
        if re.search(NOT_ON + r"(it|test)(\.\w+)*\.fails\b", line):
            return "xfail", True, "test expected to fail"
        if re.search(r"\b(ctx|context|this|t)\.skip\(\s*\)", line):
            return call("skip", "skipped test")
    elif PY.search(p):
        if re.search(
            r"\bmark\.skipif\(\s*(True|1)\s*[,)]|@unittest\.skipIf\(\s*True\b|@unittest\.skipUnless\(\s*False\b", line
        ):
            return "skip", True, "skipped test"
        if re.search(r"\bmark\.skipif\b|@unittest\.skip(If|Unless)\b|importorskip\(", line):
            return "skip", False, COND
        for rx, kind, msg in (
            (r"\bmark\.xfail\b|@unittest\.expectedFailure\b", "xfail", "test expected to fail"),
            (r"\bmark\.skip\b(?!if)|@unittest\.skip\b(?!If|Unless)", "skip", "skipped test"),
        ):
            if re.search(rx, line):
                fixed = decorated or re.search(r"pytestmark|marks\s*=", line)
                if not fixed and _indent(line) > 0:  # a marker built inside a function, such as a conftest hook
                    return kind, False, COND
                return (kind, True, msg) if fixed else call(kind, msg)
        if re.search(NOT_ON + r"pytest\.(skip|xfail)\(|\bskipTest\(", line):
            return call("skip", "skipped test")
        m = re.search(r"\bcollect_ignore(_glob)?\s*[+]?=", line)
        if m:
            return (
                ("uncollected", None, "uncollected test")
                if re.search(r"test_\w*\.py|_test\.py|tests?/", line)
                else ("uncollected", None, "files left out of test collection")
            )
    elif GO.search(p) and re.search(r"\bt\.Skip(f|Now)?\(", line):
        return call("skip", "skipped test")
    elif RS.search(p) and re.search(r"#\[ignore\b", line):
        return "skip", True, "skipped test"
    elif JVM.search(p):
        if re.search(r"@(Disabled|Enabled)(If|On)\w*", line):
            return "skip", False, COND
        if re.search(r"@(Disabled|Ignore)\b", line):
            return "skip", True, "skipped test"
    return None


def _skip_target(p, lines, i):
    """The test a skip on line i applies to: '*' for a whole module, a test name, or None if unknown."""
    line = lines[i]
    if re.search(r"^\s*pytestmark\b", line):
        return "*"
    m = re.search(r"\)\s*\(\s*[\"'`]([^\"'`]+)|\b(?:it|test|describe)(?:\.\w+)*\(\s*[\"'`]([^\"'`]+)", line)
    if m:
        return m.group(1) or m.group(2)
    if line.lstrip().startswith("@") or re.search(r"\bmarks\s*=", line):
        for l in lines[i + 1 : i + 40]:
            d = re.match(r"^\s*(?:async\s+)?def\s+(\w+)|^\s*class\s+(\w+)", l)
            if d:
                return d.group(1) or d.group(2)
        return None
    own = _indent(line)
    for k in range(i - 1, -1, -1):
        l = lines[k]
        if l.strip() and _indent(l) < own:
            d = TEST_NAMES.search(l)
            if d:
                return next(g for g in d.groups() if g)
            if re.match(r"^\s*(def|func|class)\b", l):
                return None
    return None


def _test_only(p, lines, i):
    """Blocking findings that need the code around line i of a Python test file."""
    line = lines[i]
    if re.search(r"\bexcept\s*\(?[\w.,\s]*\bAssertionError\b", line):
        own = _indent(line)
        body = [l for l in lines[i + 1 : i + 8] if l.strip()]
        block = []
        for l in body:
            if _indent(l) <= own:
                break
            block.append(l)
        if not any(re.match(r"\s*raise\b", l) for l in block):
            return "assertion failures caught"
    if re.match(r"^\s*__test__\s*=\s*False\b", line):
        own = _indent(line)
        if own == 0:
            return "test collection switched off"
        cls = next((k for k in range(i - 1, -1, -1) if lines[k].strip() and _indent(lines[k]) < own), None)
        if cls is not None and re.match(r"^\s*class\b", lines[cls]):
            end = next(
                (
                    k
                    for k in range(cls + 1, len(lines))
                    if lines[k].strip() and _indent(lines[k]) <= _indent(lines[cls])
                ),
                len(lines),
            )
            if any(re.match(r"^\s*(async\s+)?def\s+test", l) for l in lines[cls + 1 : end]):
                return "test collection switched off"
    return None


def _go_tags(lines):
    return {
        t
        for l in lines
        if re.search(r"^//go:build\s|^//\s*\+build\s", l)
        for t in re.findall(r"[A-Za-z_][\w.]*", re.sub(r"^//(go:build|\s*\+build)", "", l))
    }


def _narrow(entries, dots=False):
    """Entries that pick out part of a source tree (src/utils, orbit_analysis.charge) rather than all of it (src, src/**)."""
    out = []
    for e in entries:
        static = re.split(r"[*?{\[]", e, maxsplit=1)[0].strip("./")
        parts = [x for x in re.split(r"[/.]" if dots else r"/", static) if x]
        if dots and not re.search(r"[/.]", static):
            parts = [static]
        if len(parts) >= 2 and not re.search(r"\.(json|[cm]?[jt]sx?|py|toml|cfg)$", static):
            out.append(e)
    return out


def _norm(line):
    """A line as a formatter might leave it: quotes, spacing and trailing commas don't count."""
    return re.sub(r"\s+", " ", re.sub(r"[,;]\s*$", "", line.strip()).replace("'", '"').replace("`", '"'))


def _indent(line):
    line = line.expandtabs(4)
    return len(line) - len(line.lstrip(" "))


def _live(line):
    return line.strip() and not line.lstrip().startswith("#")


def _parents(lines, i):
    """Indices of the lines that contain line i of an indented (YAML) file, nearest first."""
    out, cur = [], _indent(lines[i])
    for k in range(i - 1, -1, -1):
        if _live(lines[k]) and _indent(lines[k]) < cur:
            out.append(k)
            cur = _indent(lines[k])
            if cur == 0:
                break
    return out


def _block(lines, k):
    end = next(
        (j for j in range(k + 1, len(lines)) if _live(lines[j]) and _indent(lines[j]) <= _indent(lines[k])), len(lines)
    )
    return "\n".join(lines[k:end])


def _ci_scope(path, text, lineno):
    """The CI job (or, in a GitHub workflow, the step) that line `lineno` belongs to, or None if unknown."""
    lines = (text or "").splitlines()
    i = lineno - 1
    if not 0 <= i < len(lines):
        return None
    chain = _parents(lines, i)
    if GITHUB_WF.search(path):
        jobs = next((n for n, k in enumerate(chain) if lines[k].strip() == "jobs:"), None)
        if jobs is None or jobs == 0:
            return None
        step = next((chain[n] for n in range(jobs - 1) if lines[chain[n]].lstrip().startswith("- ")), None)
        return _block(lines, step if step is not None else chain[jobs - 1])
    top = [k for k in chain if _indent(lines[k]) == 0]
    return _block(lines, top[0]) if top else None


def _entries(text):
    """(section, key, value) for every value under every key of a TOML, INI or JSON-style config."""
    out, header, key = [], None, None
    for raw in (text or "").splitlines():
        line = re.sub(r"(^|\s)[#;].*$", "", raw) if not raw.lstrip().startswith(('"', "'")) else raw
        if not line.strip():
            continue
        h = HEADER.match(line)
        if h and "=" not in line:
            header, key = h.group(1).strip().strip("\"'"), None
            continue
        m = KEY.match(line)
        if m:
            key, rest = m.group(1) or m.group(2) or m.group(3), m.group(4)
        elif key is None:
            continue
        else:
            rest = line
        values = re.findall(r"[\"']([^\"']*)[\"']", rest) or [v for v in re.split(r"[\s,\[\]{}]+", rest) if v]
        out += [(header, key, v.strip()) for v in values if v.strip()]
    return out


def _lint_state(texts):
    """(ignored (scope, code) pairs, selected codes, excluded paths) across ruff/flake8 configs."""
    ignored, selected, excluded = set(), set(), set()
    for text in texts:
        scope = "*"
        for header, key, v in _entries(text):
            if header and not re.search(r"ruff|flake8|pycodestyle|lint", header):
                continue
            if key in ("per-file-ignores", "extend-per-file-ignores") and ":" in v:  # flake8: path:CODE,CODE
                scope, v = [x.strip() for x in v.split(":", 1)]
            if key in ("per-file-ignores", "extend-per-file-ignores") and LINT_CODE.match(v):
                ignored.add((scope, v))
            elif key in IGNORE_KEYS and LINT_CODE.match(v):
                ignored.add(("*", v))
            elif header and header.endswith("per-file-ignores") and LINT_CODE.match(v):
                ignored.add((key, v))
            elif key in ("select", "extend-select") and LINT_CODE.match(v):
                selected.add(v)
            elif key in ("exclude", "extend-exclude"):
                excluded.add(v)
    return ignored, selected, excluded


def _values(texts, keys, section=None):
    return {
        v
        for text in texts
        for h, k, v in _entries(text)
        if k in keys and (section is None or re.search(section, h or ""))
    }


def _json_list(texts, key):
    """Top-level list values for key across JSON-with-comments files (tsconfig), or by line when they don't parse."""
    import json

    out = set()
    for text in texts:
        bare = re.sub(r"(?m)^\s*//.*$|/\*.*?\*/", "", text or "", flags=re.S)
        bare = re.sub(r",(\s*[}\]])", r"\1", bare)
        try:
            data = json.loads(bare) if bare.strip() else {}
            value = data.get(key, []) if isinstance(data, dict) else []
            out |= {v for v in value if isinstance(v, str)}
        except ValueError:
            out |= _values([text], {key})
    return out


def findings(diff, name_status, content=None, old_content=None, listing=None):
    """content(path) and old_content(path), when given, return the file after and before the change; listing(),
    every tracked path after it."""
    new = lambda p: content(p) if content else None
    old = lambda p: old_content(p) if old_content else None
    files, path, old_path, in_hunk, o, n = {}, None, None, False, 0, 0
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            path = old_path = None
            in_hunk = False
        elif not in_hunk and line.startswith("--- "):
            old_path = line[6:] if line.startswith("--- a/") else None
        elif not in_hunk and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else old_path  # a deleted file keeps its removed lines
            if path:
                files.setdefault(path, {"old": old_path or path, "minus": [], "plus": []})
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            in_hunk, o, n = True, int(m.group(1)) if m else 0, int(m.group(2)) if m else 0
        elif path and in_hunk and line.startswith("+"):
            files[path]["plus"].append((n, line[1:]))
            n += 1
        elif path and in_hunk and line.startswith("-"):
            files[path]["minus"].append((o, line[1:]))
            o += 1
    files = {p: f for p, f in files.items() if not IGNORED.search(p)}
    status = {}
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) > 1:
            status[parts[-1]] = parts
    added = lambda p: status.get(p, [""])[0] == "A"
    removed_lines = {_norm(m) for g in files.values() for _n, m in g["minus"]}
    words = lambda l: set(re.findall(r"[\w*.-]+", l))
    removed_words = set().union(*[words(m) for g in files.values() for _n, m in g["minus"]])
    reshaped = lambda l: _norm(l) in removed_lines or words(l) <= removed_words  # moved or reformatted, nothing new
    out = []

    # Line rules. For each rule, a hit counts only beyond the hits the change removes: a marker moved with its code,
    # or on a line that was only reformatted or renamed, isn't new.
    lines_of = {}

    def text_lines(p, which):
        if (p, which) not in lines_of:
            t = new(p) if which == "new" else old(files[p]["old"]) if p in files else None
            lines_of[(p, which)] = (t or "").splitlines()
        return lines_of[(p, which)]

    def prev_line(lines, lineno):
        k = lineno - 2
        while 0 <= k < len(lines) and not lines[k].strip():
            k -= 1
        return lines[k] if 0 <= k < len(lines) else ""

    def old_names(p):
        return {next(g for g in m.groups() if g) for l in text_lines(p, "old") for m in [TEST_NAMES.search(l)] if m} | {
            m.group(1) for l in text_lines(p, "old") for m in [re.match(r"^\s*class\s+(\w+)", l)] if m
        }

    outright = {}

    def outright_before(p):
        """Tests the old file skipped outright: a condition on one of them narrows the skip."""
        if p not in outright:
            lines = text_lines(p, "old")
            outright[p] = {
                _skip_target(p, lines, k)
                for k, l in enumerate(lines)
                for sk in [_skip(p, l, lines[k - 1] if k else "")]
                if sk and sk[1]
            }
        return outright[p]

    def hits(p, lineno, line, which):
        lines = text_lines(p, which)
        prev = prev_line(lines, lineno)
        res = []
        sk = _skip(p, line, prev)
        if sk:
            kind, block, what = sk
            rid = (kind, block)
            if which == "new" and 0 < lineno <= len(lines) and lines[lineno - 1] == line:
                target = _skip_target(p, lines, lineno - 1)
                existed = (target == "*" and not added(p)) or (target and target != "*" and target in old_names(p))
                if not block and existed and target not in outright_before(p):
                    what = "skipped test (an existing test now skips under a condition)"
                elif kind == "xfail" and re.search(r"strict\s*=\s*True", line) and target and not existed:
                    rid, what = (kind, False), "new test expects a known failure (strict xfail)"
                if target and target != "*" and target not in line:
                    what += " (on %s)" % target  # so an approval covers this test, not every identical marker
            res.append((rid, what))
        for files_rx, rx, what in SUPPRESS:
            m = files_rx.search(p) and re.search(rx, line)
            if m and not _in_string(line, m.start()):
                res.append((what, what))
        if PY.search(p) and TEST_FILE.search(p) and 0 < lineno <= len(lines) and lines[lineno - 1] == line:
            what = _test_only(p, lines, lineno - 1)
            if what:
                res.append((what, what))
        if p.endswith("_test.go") and re.search(GO_BUILD_IGNORE, line):
            res.append(("goignore", "test file excluded from the build"))
        for files_rx, rx, what in SOURCE_ASK + CONFIG:
            if (
                files_rx.search(p)
                and re.search(rx, line)
                and (what != "errors swallowed (an empty catch)" or TEST_FILE.search(p))
            ):
                res.append((what, what))
        if CI_FILE.search(p) and re.search(
            "(" + TEST_RUNNER + "|" + LINT_RUNNER + r")[^|#]*(\|\|\s*(true|exit\s+0|:|echo\b|cat\b)|;\s*exit\s+0\b)",
            line,
        ):
            res.append(("cifail", "a CI check allowed to fail"))
        return res

    skip_file = lambda p: GENERATED_PATH.search(p) or GENERATED.search("\n".join(text_lines(p, "new")[:12]))
    removed_by = {}
    for p, f in files.items():
        for lineno, line in f["minus"]:
            for rid, _what in hits(p, lineno, line, "old"):
                removed_by.setdefault(rid, Counter())[p] += 1
                removed_by[rid]["*"] += 1
                removed_by[rid][("text", _norm(line))] += 1
    added_by = {}
    for p, f in files.items():
        if skip_file(p):
            continue
        for lineno, line in f["plus"]:
            for rid, what in hits(p, lineno, line, "new"):
                added_by.setdefault(rid, []).append((p, line, what))
    credit = {"@ts-expect-error without a reason": "TypeScript suppression (use @ts-expect-error -- <reason>)"}
    for rid, adds in added_by.items():
        gone_ = removed_by.get(rid, Counter()) + removed_by.get(credit.get(rid), Counter())
        extra = len(adds) - gone_["*"]
        if extra <= 0:
            continue
        per_file = Counter(p for p, _l, _w in adds)
        fresh = [(p, l, w) for p, l, w in adds if per_file[p] > gone_[p] and not gone_[("text", _norm(l))]]
        fresh += [(p, l, w) for p, l, w in adds if per_file[p] > gone_[p] and (p, l, w) not in fresh]
        for p, l, w in fresh[:extra]:
            out.append((p, "%s: %s" % (w, l.strip()[:100])))

    # Go build constraints: a tag that isn't a platform moves an existing test out of plain `go test`.
    for p, f in files.items():
        if p.endswith("_test.go") and f["plus"]:
            tags = sorted(
                t
                for t in _go_tags(text_lines(p, "new")) - _go_tags(text_lines(p, "old"))
                if not GO_PLATFORM.match(t) and t != "ignore"
            )
            if tags:
                out.append(
                    (
                        p,
                        "%s (plain go test skips it): %s"
                        % (
                            "new test file behind a build tag" if added(p) else "test moved behind a build tag",
                            " ".join(tags),
                        ),
                    )
                )

    of = lambda rx: [(p, f) for p, f in files.items() if rx.search(p)]

    # CI: a job that runs tests allowed to fail, switched off or made manual (a deploy job may be either).
    old_lines_of = lambda p: text_lines(p, "old")
    for p, f in of(CI_FILE):
        text = new(p)
        for lineno, line in f["plus"]:
            if (ALLOW_FAIL.search(line) or (WHEN_OFF.search(line) and not GITHUB_WF.search(p))) and _norm(
                line
            ) not in removed_lines:
                scope = _ci_scope(p, text, lineno)
                if scope is None or re.search(TEST_RUNNER + "|" + LINT_RUNNER, scope) or re.match(r"default:", scope):
                    what = (
                        "a CI check job allowed to fail"
                        if ALLOW_FAIL.search(line)
                        else "a CI check job switched off or made manual"
                    )
                    out.append((p, "%s: %s" % (what, line.strip()[:100])))
        lines = (text or "").splitlines()
        lenient = {
            m.group(1)
            for k, l in enumerate(lines)
            for m in [re.match(r"^(\.[^#:]+):\s*$", l)]
            if m and re.search(r"allow_failure:\s*true|when:\s*(manual|never)", _block(lines, k))
        }
        for lineno, line in f["plus"]:
            m = re.search(r"^\s*extends:\s*(.*)$", line)
            scope = _ci_scope(p, text, lineno) if m else None
            if (
                m
                and scope
                and re.search(TEST_RUNNER + "|" + LINT_RUNNER, scope)
                and any(t in lenient for t in re.findall(r"\.[\w:-]+", m.group(1)))
            ):
                out.append((p, "a CI check job now extends a template that may not fail it: %s" % line.strip()))
            if (
                re.match(r"^\s*-\s*if:|^\s*only:|^\s*except:", line)
                and not GITHUB_WF.search(p)
                and _norm(line) not in removed_lines
            ):
                scope = _ci_scope(p, text, lineno)
                job = scope.splitlines()[0].strip() if scope else ""
                olds_ = old_lines_of(p)
                k_old = next((k for k, l in enumerate(olds_) if job and l.strip() == job), None)
                was_limited = k_old is not None and re.search(r"^\s*(only|except|rules):", _block(olds_, k_old), re.M)
                if (
                    scope
                    and k_old is not None
                    and not was_limited
                    and re.search(TEST_RUNNER, scope)
                    and not re.search(r"changes:|merge_request_event", scope)
                ):
                    out.append((p, "a CI test job now runs only under conditions: %s" % line.strip()[:100]))
            if (
                re.search(TEST_RUNNER, line)
                and re.search(r"\s(\S+/)?(test_\w+\.py|\w+_test\.(py|go)|\S+\.(test|spec)\.[jt]sx?)\b|::", line)
                and not any(
                    re.search(r"(test_\w+\.py|_test\.(py|go)|\.(test|spec)\.[jt]sx?)\b|::", m_) for _n, m_ in f["minus"]
                )
            ):
                out.append((p, "tests narrowed to specific files: %s" % line.strip()[:100]))
        hidden = {m.group(1) for _n, l in f["minus"] for m in [re.match(r"^([A-Za-z0-9_][^#]*?):\s*$", l)] if m}
        for _n, line in f["plus"]:
            m = re.match(r"^\.([^#]+?):\s*$", line)
            if m and m.group(1) in hidden:
                out.append((p, "a CI job hidden, so it no longer runs: %s" % m.group(1)))

    # Tests deselected, excluded or rerun, or coverage switched off: in pytest config, test scripts and CI test lines.
    def deselects(lines, p):
        for _n, line in lines:
            if (
                PYTEST_FILE.search(p)
                or (PACKAGE_JSON.search(p) and re.search(r"\"test", line))
                or (CI_FILE.search(p) and re.search(TEST_RUNNER + r"|PYTEST_ADDOPTS", line))
            ):
                flat = re.sub(r"[\"',\[\]]", " ", line)
                for t in DESELECT.finditer(flat):
                    yield p, re.sub(r"\s+", " ", t.group(0).strip())

    before = Counter(t for p, f in files.items() for _p, t in deselects(f["minus"], p))
    for p, f in files.items():
        for _p, t in deselects(f["plus"], p):
            if before[t]:
                before[t] -= 1
                continue
            what = (
                "coverage switched off"
                if t.startswith("--no-cov")
                else "collection errors ignored"
                if t.startswith("--continue-on")
                else "failing tests rerun until they pass"
                if t.startswith("--reruns")
                else "tests deselected or excluded"
            )
            out.append((p, "%s: %s" % (what, t)))

    # Config compared as a whole, before and after, across every file of a kind in the change. A path entry that
    # follows a renamed file is the same entry.
    renames = [(parts[1], parts[2]) for parts in status.values() if parts[0].startswith("R") and len(parts) > 2]

    def moved(entry):
        sep = "/" if "/" in entry or entry.endswith(".py") else "."
        for src, dst in renames:
            if sep == ".":
                src, dst = (re.sub(r"^(.*/)?src/|\.py$", "", x).replace("/", ".") for x in (src, dst))
            e, sc, dc = entry.strip(sep).split(sep), src.split(sep), dst.split(sep)
            if len(e) <= len(sc) and sc[len(sc) - len(e) :] == e:
                pre = sc[: len(sc) - len(e)]
                if dc[: len(pre)] == pre:
                    return sep.join(dc[len(pre) :])
        return entry

    def states(rx):
        sel = [p for p in files if rx.search(p)]
        return [old(files[p]["old"]) or "" for p in sel], [new(p) or "" for p in sel], sel

    if content:
        olds, news, sel = states(PY_LINT_FILE)
        if sel:
            ig0, se0, ex0 = _lint_state(olds)
            ig1, se1, ex1 = _lint_state(news)
            ig0 |= {(moved(sc), c) for sc, c in ig0}
            ex0 |= {moved(x) for x in ex0}
            fresh = se1 - se0
            for scope, code in sorted(ig1 - ig0):
                if ("*", code) in ig0 and code != "ALL":
                    continue  # a global ignore narrowed to some files
                if code == "ALL" or not any(code.startswith(f) for f in fresh):
                    out.append(
                        (sel[0], "lint rule ignored in config: %s%s" % (code, "" if scope == "*" else " (%s)" % scope))
                    )
            for code in sorted(se0 - se1):
                if "ALL" not in se1 and not any(code.startswith(f) for f in se1):
                    out.append((sel[0], "lint rule no longer selected: %s" % code))
            for path_ in sorted(ex1 - ex0):
                out.append((sel[0], "files excluded from linting: %s" % path_))
            limit = lambda texts: {
                k: float(v)
                for t in texts
                for h, k, v in _entries(t)
                if re.match(r"(max-)?line-length$|max-(complexity|args|branches|statements|returns|locals)$", k)
                and re.match(r"^\d+(\.\d+)?$", v)
            }
            l0, l1 = limit(olds), limit(news)
            for k in sorted(k for k in l1 if k in l0 and l1[k] > l0[k]):
                out.append((sel[0], "lint limit raised: %s %g -> %g" % (k, l0[k], l1[k])))
        olds, news, sel = states(PYTEST_FILE)
        if sel:
            tp0, tp1 = _values(olds, {"testpaths"}), _values(news, {"testpaths"})
            if tp1:
                for t in sorted(tp0 - tp1):
                    out.append((sel[0], "test paths narrowed: %s no longer collected" % t))
            for d in sorted(_values(news, {"norecursedirs"}) - _values(olds, {"norecursedirs"})):
                out.append((sel[0], "directories hidden from test collection: %s" % d))
        olds, news, sel = states(PY_COVERAGE_FILE)
        if sel:
            omit0 = _values(olds, {"omit"}, r"coverage|^run$|^report$")
            for o_ in sorted(_values(news, {"omit"}, r"coverage|^run$|^report$") - omit0 - {moved(x) for x in omit0}):
                out.append((sel[0], "code excluded from coverage in config: %s" % o_))
        olds, news, sel = states(MYPY_FILE)
        if sel:
            strict = lambda texts: any(
                k == "strict" and v.lower() == "true" and re.search(r"mypy", h or "")
                for t in texts
                for h, k, v in _entries(t)
            )
            if strict(olds) and not strict(news):
                out.append((sel[0], "mypy strict mode removed"))
        olds, news, sel = states(MYPY_FILE)
        if sel:
            glob_ = lambda texts: any(
                k == "ignore_missing_imports" and v.lower() == "true" and re.match(r"^(tool\.)?mypy$", h or "")
                for t in texts
                for h, k, v in _entries(t)
            )
            if glob_(news) and not glob_(olds):
                out.append((sel[0], "type checking loosened: ignore_missing_imports for every module"))
            for x in sorted(_values(news, {"exclude"}, r"mypy") - _values(olds, {"exclude"}, r"mypy")):
                out.append((sel[0], "files excluded from type checking: %s" % x))
        olds, news, sel = states(PY_COVERAGE_FILE)
        if sel:
            cov_sec = r"coverage|^run$|^report$"
            src0, src1 = _values(olds, {"source", "include"}, cov_sec), _values(news, {"source", "include"}, cov_sec)
            if src1 and not src0 and _narrow(src1, dots=True):
                out.append((sel[0], "coverage now measures only: %s" % ", ".join(sorted(src1))))
            elif src1:
                for x in sorted(src0 - src1):
                    out.append((sel[0], "coverage no longer measures: %s" % x))
            idiom = (
                r"TYPE_CHECKING|abstractmethod|NotImplementedError|__name__|pragma|__repr__|@overload|Protocol|^if 0|"
                r"^\\?\.\\?\.\\?\.|assert_never|AssertionError"
            )
            for x in sorted(
                _values(news, {"exclude_also", "exclude_lines"}, cov_sec)
                - _values(olds, {"exclude_also", "exclude_lines"}, cov_sec)
            ):
                if not re.search(idiom, x):
                    out.append((sel[0], "code excluded from coverage in config: %s" % x))
        olds, news, sel = states(PYTEST_FILE)
        if sel:
            for key_ in ("python_files", "python_functions", "python_classes"):
                if _values(olds, {key_}) != _values(news, {key_}):
                    out.append((sel[0], "test discovery changed: %s" % key_))
            strictness = lambda texts: {
                t
                for text in texts
                for t in re.findall(
                    r"--strict-markers|--strict-config|--strict\b|-W\s*error\b|"
                    r"^\s*[\"']?error[\"']?,?\s*$",
                    text,
                    re.M,
                )
            }
            for x in sorted(strictness(olds) - strictness(news)):
                out.append((sel[0], "pytest strictness removed: %s" % x.strip().strip("\"',")))
        olds, news, sel = states(TSCONFIG)
        if sel:
            inc0, inc1 = _json_list(olds, "include"), _json_list(news, "include")
            if inc1 and not inc0 and _narrow(inc1) and not any(re.search(r"(\.test|\.spec|test)", x) for x in inc1):
                out.append((sel[0], "type checking limited to: %s" % ", ".join(sorted(inc1))))
            elif inc1:
                for x in sorted(inc0 - inc1):
                    if not any(x.startswith(y.rstrip("*/")) or y.startswith(x.rstrip("*/")) for y in inc1):
                        out.append((sel[0], "files no longer type-checked: %s" % x))
            for x in sorted(_json_list(news, "exclude") - _json_list(olds, "exclude")):
                if not re.search(BUILD_DIRS, x.strip("/")):
                    out.append((sel[0], "files excluded from type checking: %s" % x))
    build_dirs = BUILD_DIRS
    for p, f in of(JS_TEST_CONFIG):
        lines = (new(p) or "").splitlines()
        for lineno, line in f["plus"]:
            if (
                re.search(r"\binclude\b", line)
                and _norm(line) not in removed_lines
                and _narrow(re.findall(r"[\"'`]([^\"'`]+)[\"'`]", line.split("include", 1)[1]))
            ):
                out.append((p, "the files a test run or coverage covers narrowed: %s" % line.strip()[:100]))
            if not re.search(r"\bexclude\b", line) or _norm(line) in removed_lines:
                continue
            if re.search(r"\bcoverage\b.*\bexclude\b", line) or (
                0 < lineno <= len(lines)
                and any(re.search(r"\bcoverage\b", lines[k]) for k in _parents(lines, lineno - 1))
            ):
                globs = re.findall(r"[\"'`]([^\"'`]+)[\"'`]", line.split("exclude", 1)[1])
                if not globs or any(
                    not re.search(build_dirs, g.strip("/*")) and not re.search(r"\.(test|spec|stories)\.", g)
                    for g in globs
                ):
                    out.append((p, "code excluded from coverage in config: %s" % line.strip()[:100]))
            elif any(
                not re.search(build_dirs, x.strip("/*"))
                for x in re.findall(r"[\"'`]([^\"'`]+)[\"'`]", line.split("exclude", 1)[1])
            ):
                out.append((p, "tests excluded in config: %s" % line.strip()[:100]))
    for p, f in of(ESLINT_FILE):
        for _n, line in f["plus"]:
            if re.search(r"\b(ignores|ignorePatterns)\b", line) and _norm(line) not in removed_lines:
                globs = re.findall(r"[\"'`]([^\"'`]+)[\"'`]", line.split(":", 1)[-1])
                was = {
                    g.strip("./*")
                    for q, g_ in files.items()
                    if ESLINT_FILE.search(q) or q.endswith(".eslintignore")
                    for _n, m in g_["minus"]
                    for g in (re.findall(r"[\"'`]([^\"'`]+)[\"'`]", m) or [m.strip()])
                }
                if any(
                    not re.search(build_dirs, g.strip("/")) and g.strip("./*") not in was
                    for g in globs
                    if g not in ("ignores", "ignorePatterns")
                ):
                    out.append((p, "files excluded from ESLint: %s" % line.strip()[:100]))

    # ESLint rules switched off or downgraded, read across every ESLint config in the change.
    eslint = of(ESLINT_FILE)
    level = lambda m: {"0": "off", "1": "warn", "2": "error"}.get(m.group(3), m.group(2))

    def levels(line):  # (rule, level), skipping option objects such as ["error", 2, { "SwitchCase": 0 }]
        for m in ESLINT_LEVEL.finditer(line):
            if re.search(r"\[\s*([\"'](off|warn|error)[\"']|[012])\s*,[^\]]*\{[^}]*$", line[: m.start()]):
                continue
            if m.group(3) and not ("-" in m.group(1) or "/" in m.group(1) or m.group(1) in ESLINT_ONE_WORD):
                continue
            yield m.group(1), level(m)

    was = {}
    for _p, f in eslint:
        for _n, l in f["minus"]:
            for rule, lv in levels(l):
                was.setdefault(rule, set()).add(lv)
    now = {rule: lv for _p, f in eslint for _n, l in f["plus"] for rule, lv in levels(l)}
    replaced = {r.split("/")[-1] for r, lv in now.items() if "/" in r and lv in ("warn", "error")}
    for rule in sorted(r for r, lvs in was.items() if lvs & {"warn", "error"} and r not in now):
        out.append((eslint[0][0], "ESLint rule removed: %s" % rule))
    for p, f in eslint:
        for _n, line in f["plus"]:
            for rule, lv in levels(line):
                if lv == "off" and "off" not in was.get(rule, set()) and rule not in replaced:
                    out.append((p, "ESLint rule switched off: %s" % rule))
                elif lv == "warn" and "error" in was.get(rule, set()):
                    out.append((p, "ESLint rule downgraded to a warning: %s" % rule))

    def family(preset):  # eslint:recommended and js.configs.recommended are the same preset, and so on
        parts = [
            t
            for t in re.split(r"[:/.]", preset)
            if t and t not in ("plugin", "configs", "config", "flat", "recommended")
        ]
        name = parts[0] if parts else preset
        return {
            "js": "eslint",
            "@eslint": "eslint",
            "tseslint": "@typescript-eslint",
            "typescript-eslint": "@typescript-eslint",
        }.get(name, name)

    presets = lambda lines: {m for _n, l in lines for m in re.findall(r"[\w@/:.-]*recommended[\w-]*", l)}
    kept = {family(m) for _q, g in eslint for m in presets(g["plus"])}
    for p, f in eslint:
        for preset in sorted(m for m in presets(f["minus"]) if family(m) not in kept):
            out.append((p, "ESLint preset removed: %s" % preset))
    for p, f in of(PACKAGE_JSON):
        script = lambda lines: {
            m.group(1): m.group(2)
            for _n, l in lines
            for m in re.finditer(
                r"\"((?:test|lint|typecheck|type-check|check|build|ci|verify|validate)[\w:-]*)\"\s*:\s*\"([^\"]*)\"", l
            )
        }
        before, after = script(f["minus"]), script(f["plus"])
        for name in sorted(set(before) & set(after)):
            tools = lambda v: set(
                re.findall(r"\b(tsc|eslint|vitest|jest|playwright|pytest|ruff|mypy|prettier|stylelint)\b", v)
            )
            lost = tools(before[name]) - tools(after[name])
            if lost:
                out.append((p, "a check removed from the %s script: %s" % (name, ", ".join(sorted(lost)))))
            elif (
                name.startswith(("test", "lint"))
                and re.search(r"\s(\./)?[\w-]+/[\w./*-]*", after[name])
                and not re.search(r"\s(\./)?[\w-]+/[\w./*-]*", before[name])
            ):
                out.append((p, "the %s script narrowed to a path: %s" % (name, after[name][:80])))

    for p, f in files.items():
        if PY.search(p) and TEST_FILE.search(p):
            for _n, line in f["plus"]:
                hook = re.match(
                    r"^\s*def\s+(pytest_ignore_collect|pytest_collection_modifyitems|pytest_collect_file)\b", line
                )
                if hook and _norm(line) not in removed_lines:
                    out.append((p, "tests filtered by a collection hook: %s" % hook.group(1)))
        if CODE.search(p) and TEST_FILE.search(p):
            lines = text_lines(p, "new")
            for lineno, line in f["plus"]:
                if re.search(r"\bcatch\b[^{]*\{\s*$|^\s*except\b[^:]*:\s*$", line) and 0 < lineno <= len(lines):
                    body = []
                    for l in lines[lineno : lineno + 6]:
                        if re.match(r"^\s*\}", l) or (l.strip() and _indent(l) <= _indent(line)):
                            break
                        body.append(l)
                    if all(not l.strip() or re.match(r"^\s*(//|#|pass\b|\.\.\.)", l) for l in body):
                        out.append((p, "errors swallowed in a test: %s" % line.strip()[:100]))

    if content:
        olds, news, sel = states(PYTEST_FILE)
        if sel:
            warn = lambda texts: {v for v in _values(texts, {"filterwarnings"}) if v.startswith("ignore")}
            strict_before = any(v.strip() == "error" for v in _values(olds, {"filterwarnings"}))
            for x in sorted(warn(news) - warn(olds)):
                fields = x.split(":")
                if strict_before and not (len(fields) >= 4 and fields[3].strip()):  # one third-party module is fine
                    out.append((sel[0], "warnings ignored in tests: %s" % x))
        olds, news, sel = states(MYPY_FILE)
        if sel:

            def off_modules(texts):  # modules whose type errors are switched off in overrides
                mods = set()
                for t in texts:
                    for sec in re.split(r"(?m)^\s*\[\[?", t):
                        head = sec.split("]", 1)[0]
                        if re.search(r"ignore_errors\s*=\s*(true|True)", sec):
                            mods |= set(re.findall(r"mypy-([\w.*,-]+)", "[" + head)) | set(
                                re.findall(
                                    r"[\"']([\w.*]+)[\"']",
                                    (re.search(r"module\s*=\s*(\[[^\]]*\]|\S+)", sec) or [""])[0],
                                )
                            )
                return {m for x in mods for m in x.split(",")}

            for m in sorted(off_modules(news) - off_modules(olds) - {moved(x) for x in off_modules(olds)}):
                out.append((sel[0], "type checking switched off for: %s" % m))
    for p, f in files.items():
        if re.search(r"(^|/)\.golangci\.ya?ml$", p):
            lines = text_lines(p, "new")
            for lineno, line in f["plus"]:
                if (
                    reshaped(line)
                    or not line.strip()
                    or not 0 < lineno <= len(lines)
                    or re.match(r"^\s*-?\s*[\w-]+:\s*$", line)
                ):
                    continue  # moved, reformatted, or only a key that holds the entries below it
                chain = [lines[k] for k in _parents(lines, lineno - 1)] + [line]
                if any(re.search(r"exclude|disable\b|exclusions|skip-(dirs|files)", c) for c in chain):
                    out.append((p, "Go lint exclusion added: %s" % line.strip()[:100]))
        if TEST_FILE.search(p) and (PY.search(p) or JS.search(p) or GO.search(p)):
            old_conds = [l for _n, l in f["minus"] if _skip(p, l, "") and not _skip(p, l, "")[1]]
            for _n, line in f["plus"]:
                sk = _skip(p, line, "")
                if not sk or sk[1] or _norm(line) in removed_lines or not old_conds:
                    continue
                ci = r"[\"']CI[\"']|\bCI\b|GITLAB_CI|GITHUB_ACTIONS"
                ops = lambda l: len(re.findall(r"\bor\b|\|\|", l))
                if (re.search(ci, line) and not any(re.search(ci, o) for o in old_conds)) or ops(line) > max(
                    ops(o) for o in old_conds
                ):
                    out.append((p, "a skip condition widened: %s" % line.strip()[:100]))
        if PY.search(p) and TEST_FILE.search(p):
            entries = lambda lines: {
                x
                for _n, l in lines
                if re.search(r"\bcollect_ignore(_glob)?\b", l)
                for x in re.findall(r"[\"']([^\"']+)[\"']", l)
            }
            for x in sorted(entries(f["plus"]) - entries(f["minus"])):
                if any(re.search(r"\bcollect_ignore", l) for _n, l in f["minus"]):
                    out.append(
                        (
                            p,
                            "%s: %s"
                            % (
                                "uncollected test"
                                if re.search(r"test_\w*\.py|_test\.py|tests?/", x)
                                else "files left out of test collection",
                                x,
                            ),
                        )
                    )
            if p.endswith("conftest.py"):
                lines = text_lines(p, "new")
                for lineno, line in f["plus"]:
                    if not line.strip() or reshaped(line) or _skip(p, line, "") or not 0 < lineno <= len(lines):
                        continue
                    chain = [lines[k] for k in _parents(lines, lineno - 1)] + [line]
                    if any(
                        re.search(
                            r"(?i)xfail|skip|ignore|known_fail|flaky|quarantin|pytest_collection_modifyitems|"
                            r"pytest_ignore_collect|pytest_runtest_setup",
                            c,
                        )
                        for c in chain
                    ):
                        out.append((p, "a conftest change touches skips or expected failures: %s" % line.strip()[:100]))
                        break

    # Git hooks the repo runs before a commit: pre-commit hooks removed, husky or lefthook commands emptied.
    for p, f in files.items():
        if re.search(r"(^|/)\.pre-commit-config\.ya?ml$", p):
            gone_ids = sum(1 for _n, l in f["minus"] if re.match(r"^\s*-\s*id:", l)) - sum(
                1 for _n, l in f["plus"] if re.match(r"^\s*-\s*id:", l)
            )
            if gone_ids > 0:
                out.append((p, "pre-commit hooks removed (%d)" % gone_ids))
        elif re.search(r"(^|/)\.husky/[\w-]+$", p):
            cmds = lambda lines: [l for _n, l in lines if _live(l) and not re.match(r"^\s*(\.|source)\s|^\s*#!", l)]
            if len(cmds(f["minus"])) > len(cmds(f["plus"])) or any(
                re.match(r"^\s*exit\s+0\b", l) for _n, l in f["plus"]
            ):
                out.append((p, "a git hook emptied or bypassed"))

    # TypeScript strict mode removed (unless strict is set elsewhere, or the file now extends a base config).
    strict_elsewhere = any(re.search(r"\"strict\"\s*:\s*true", l) for _p, f in of(TSCONFIG) for _n, l in f["plus"])
    for p, f in of(TSCONFIG):
        minus, plus = [l for _n, l in f["minus"]], [l for _n, l in f["plus"]]
        if (
            any(re.search(r"\"strict\"\s*:\s*true", l) for l in minus)
            and not any(re.search(r"\"strict\"", l) for l in plus)
            and not strict_elsewhere
            and not any(re.search(r"\"(extends|references)\"", l) for l in plus)
        ):
            out.append((p, "TypeScript strict mode removed"))

    # CI test steps and coverage thresholds, counted across all CI and coverage files in the change.
    ci = of(CI_FILE)
    for label, rx in (("test", CI_TEST), ("lint or type-check", re.compile(LINT_RUNNER))):
        step = lambda l: _live(l) and any(rx.search(s) and not INSTALL.search(s) for s in re.split(r"&&|\|\||;", l))
        removed = sum(1 for _p, f in ci for _n, l in f["minus"] if step(l))
        added_ = sum(1 for _p, f in ci for _n, l in f["plus"] if step(l))
        if removed > added_:
            out.append(("(CI)", "%s steps removed from CI (%d removed, %d added)" % (label, removed, added_)))
    go_all = any(re.search(r"\bgo test\b.*\./\.\.\.", l) for _p, f in ci for _n, l in f["minus"])
    for p, f in ci:
        for _n, l in f["plus"]:
            if go_all and re.search(r"\bgo test\b", l) and not re.search(r"\./\.\.\.", l):
                out.append((p, "tests narrowed: %s" % l.strip()[:100]))
    olds_, news_ = {}, {}
    key = lambda k: "fail_under" if re.search(r"fail[_-]under", k, re.I) else k.lower()
    cov = of(COVERAGE_FILE)
    for _p, f in cov:
        for lines, into in ((f["minus"], olds_), (f["plus"], news_)):
            for _n, line in lines:
                for k, v in COVERAGE_KEY.findall(line):
                    into.setdefault(key(k), []).append(float(v))
    if listing and any(not news_.get(k) or max(news_[k]) < max(v) for k, v in olds_.items()):
        # A threshold the change drops may still be set in a file it doesn't touch (pytest-cov falls back to
        # coverage's fail_under, say): count those files on both sides.
        for q in listing():
            if COVERAGE_FILE.search(q) and q not in files and not IGNORED.search(q):
                for k, v in COVERAGE_KEY.findall(new(q) or ""):
                    for into in (olds_, news_):
                        into.setdefault(key(k), []).append(float(v))
    for k, before_ in olds_.items():
        after = news_.get(k, [])
        if not after:
            out.append(("(coverage)", "coverage threshold removed: %s %s" % (k, max(before_))))
        elif (len(after) == len(before_) and min(after) < min(before_)) or max(after) < max(before_):
            low = max(after) < max(before_)
            out.append(
                (
                    "(coverage)",
                    "coverage threshold lowered: %s %s -> %s"
                    % (k, max(before_) if low else min(before_), max(after) if low else min(after)),
                )
            )
    for k, after in news_.items():
        if k not in olds_ and "fail" in k and min(after) == 0:
            out.append(("(coverage)", "coverage threshold set to 0: %s" % k))
    if (
        any(THRESHOLD_BLOCK.search(l) for _p, f in cov for _n, l in f["minus"])
        and not olds_
        and not any(THRESHOLD_BLOCK.search(l) for _p, f in cov for _n, l in f["plus"])
    ):
        out.append(("(coverage)", "coverage threshold removed"))

    # Fewer tests or assertions overall (moving tests between files is neutral), with the tests that went.
    names = lambda lines: Counter(
        next(g for g in m.groups() if g) for _n, l in lines for m in [TEST_NAMES.search(l)] if m
    )
    counted = [
        (p, f) for p, f in files.items() if TEST_FILE.search(p) and CODE.search(p) and not p.endswith("conftest.py")
    ]
    code_ = lambda l: not l.lstrip().startswith(("//", "#", "/*", "*"))
    removed_t = sum(1 for _p, f in counted for _n, l in f["minus"] if TEST_DEF.search(l) and code_(l))
    added_t = sum(1 for _p, f in counted for _n, l in f["plus"] if TEST_DEF.search(l) and code_(l))
    table = any(
        re.search(
            r"mark\.parametrize|\.each\s*[(`]|\[\]struct\s*\{|for\s+_,\s*\w+\s*:=\s*range|@ParameterizedTest|"
            r"pytest\.param\(|subTest\(",
            l,
        )
        for _p, f in counted
        for _n, l in f["plus"]
    )
    gone_names = sum((names(f["minus"]) for _p, f in counted), Counter()) - sum(
        (names(f["plus"]) for _p, f in counted), Counter()
    )
    if removed_t > added_t:
        listed = ", ".join(sorted(gone_names)[:5]) + (", ..." if len(gone_names) > 5 else "")
        out.append(
            (
                "(tests)",
                "%d fewer test definitions than before (%d removed, %d added%s)%s"
                % (
                    removed_t - added_t,
                    removed_t,
                    added_t,
                    "; gone: " + listed if listed else "",
                    "; a parametrized or table test was added, so check its cases cover the ones removed"
                    if table
                    else "",
                ),
            )
        )
    else:
        removed_a = sum(1 for _p, f in counted for _n, l in f["minus"] if ASSERTION.search(l) and code_(l))
        added_a = sum(1 for _p, f in counted for _n, l in f["plus"] if ASSERTION.search(l) and code_(l))
        if removed_a > added_a:
            out.append(
                (
                    "(tests)",
                    "%d fewer assertions than before (%d removed, %d added)%s"
                    % (
                        removed_a - added_a,
                        removed_a,
                        added_a,
                        "; a parametrized or table test was added" if table else "",
                    ),
                )
            )

    # Test files deleted (unless their tests reappear elsewhere in the change), moved out of the test tree, or
    # renamed so the runner may not collect them.
    everywhere = sum((names(f["plus"]) for f in files.values()), Counter())
    for parts in status.values():
        kind, src = parts[0], parts[1]
        if kind == "D" and TEST_FILE.search(src) and CODE.search(src) and not IGNORED.search(src):
            lost = [t for t in names(files.get(src, {"minus": []})["minus"]) if not everywhere[t]]
            defined = any(TEST_DEF.search(l) for _n, l in files.get(src, {"minus": []})["minus"])
            if lost or (defined and not names(files.get(src, {"minus": []})["minus"])):
                out.append(
                    (src, "test file deleted%s" % (" (tests gone: %s)" % ", ".join(sorted(lost)[:5]) if lost else ""))
                )
        if kind.startswith("R") and len(parts) > 2 and CODE.search(src):
            dst = parts[2]
            text = new(dst)
            defines = text is None or any(TEST_DEF.search(l) for l in text.splitlines())
            if TEST_FILE.search(src) and not TEST_FILE.search(dst) and defines:
                out.append((dst, "test file moved out of the test tree (from %s)" % src))
            elif TEST_NAME.search(src) and not TEST_NAME.search(dst) and defines:
                out.append((dst, "test file renamed so the runner may not collect it (from %s)" % src))

    # An assertion in a test that already existed, changed or removed (a weakened expectation reads as an ordinary
    # edit, so ask). Only lines that don't reappear in the file, reformatted or not.
    def shape(l):  # identifiers abstracted (renames, a sharper matcher); literals and structure kept
        if TEST_DEF.search(l):
            l = re.sub(r"([\"'`]).*?\1", "S", l, count=1)  # the test's own name
        return re.sub(r"\s+", "", re.sub(r"\b[A-Za-z_]\w*\b", "I", l))

    plus = [l for _p, f in counted for _n, l in f["plus"]]  # moving assertions between test files is neutral
    plus_norm, plus_shape = {_norm(l) for l in plus}, {shape(l) for l in plus}
    plus_words = set().union(*[words(l) for l in plus]) if plus else set()
    for p, f in counted:
        if added(p) or status.get(p, [""])[0] == "D":
            continue
        changed = [
            l
            for _n, l in f["minus"]
            if ASSERTION.search(l)
            and code_(l)
            and _norm(l) not in plus_norm
            and shape(l) not in plus_shape
            and not words(l) <= plus_words
        ]
        if changed:
            out.append(
                (
                    p,
                    "assertion changed or removed in an existing test%s: %s"
                    % (" (%d)" % len(changed) if len(changed) > 1 else "", changed[0].strip()[:100]),
                )
            )

    # A skip that now sits on a different test (the count stays the same, so the line rules above don't see it), and
    # module-wide conditions or collection hooks added to existing test files.
    def outright_targets(p, which):
        lines = text_lines(p, which)
        return {
            _skip_target(p, lines, k)
            for k, l in enumerate(lines)
            for sk in [_skip(p, l, lines[k - 1] if k else "")]
            if sk and sk[1]
        } - {None, "*"}

    old_t, new_t = set(), set()
    for p in files:
        if TEST_FILE.search(p) and CODE.search(p) and not added(p):
            old_t |= outright_targets(p, "old")
            new_t |= outright_targets(p, "new")
    if new_t - old_t and old_t - new_t:
        out.append(
            (
                "(tests)",
                "a skip moved to a different test: now %s, no longer %s"
                % (", ".join(sorted(new_t - old_t)[:3]), ", ".join(sorted(old_t - new_t)[:3])),
            )
        )
    for p, f in files.items():
        if added(p) or not (TEST_FILE.search(p) and PY.search(p)):
            continue
        for _n, l in f["plus"]:
            if reshaped(l):
                continue
            if re.match(r"^\S.*\bpytest\.importorskip\s*\(", l) or re.match(r"^\w+\s*=\s*pytest\.importorskip\s*\(", l):
                out.append((p, "a module-level importorskip added to an existing test file: %s" % l.strip()[:100]))
            if p.endswith("conftest.py") and re.search(
                r"def\s+pytest_collection_modifyitems\b|add_marker\(\s*pytest\.mark\.(skip|xfail)", l
            ):
                out.append((p, "a conftest hook that skips or deselects tests: %s" % l.strip()[:100]))

    # CONSTRAINTS.md, the written quality bar: a rule changed or removed, or an exception added.
    for p, f in files.items():
        if not re.search(r"(^|/)CONSTRAINTS\.md$", p):
            continue
        plus_norm = {_norm(l) for _n, l in f["plus"]}
        for _n, l in f["minus"]:
            if re.match(r"^\s*(\||[-*]\s)", l) and not re.match(r"^\s*\|[\s|:-]*$", l) and _norm(l) not in plus_norm:
                out.append((p, "a written constraint changed or removed: %s" % l.strip()[:100]))
        lines, section = text_lines(p, "new"), ""
        for k, l in enumerate(lines, 1):
            if l.startswith("#"):
                section = l.lower()
            elif (
                "exception" in section
                and re.match(r"^\s*\|", l)
                and not re.match(r"^\s*\|[\s|:-]*$", l)
                and any(n == k for n, _l in f["plus"])
                and not re.search(r"\|\s*ID\s*\|", l)
            ):
                out.append((p, "a constraint exception added: %s" % l.strip()[:100]))

    seen, unique = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def git(args, cwd=None, env=None):
    r = subprocess.run(["git"] + args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout


def check(diff_args, cwd=None, env=None):
    """Findings for `git diff <diff_args>` in cwd (env can point GIT_INDEX_FILE at a replayed index)."""
    revs = [a for a in diff_args if not a.startswith("-")]
    if len(revs) == 1 and ".." in revs[0]:
        three = "..." in revs[0]
        a, b = revs[0].split("..." if three else "..", 1)
        old_rev, new_rev = a or "HEAD", b or "HEAD"
        if three:
            try:
                old_rev = git(["merge-base", old_rev, new_rev], cwd, env).strip()
            except RuntimeError:
                pass
    elif "--cached" in diff_args:
        old_rev, new_rev = (revs[0] if revs else "HEAD"), ":"
    elif len(revs) >= 2:
        old_rev, new_rev = revs[0], revs[1]
    else:
        old_rev, new_rev = (revs[0] if revs else "HEAD"), None

    def show(rev, path):
        try:
            if rev is None:
                with open(os.path.join(cwd or ".", path)) as f:
                    return f.read()
            return git(["show", (":" if rev == ":" else rev + ":") + path], cwd, env)
        except (RuntimeError, OSError):
            return None

    def listing():
        try:
            if new_rev in (":", None):
                return git(["ls-files"], cwd, env).splitlines()
            return git(["ls-tree", "-r", "--name-only", new_rev], cwd, env).splitlines()
        except RuntimeError:
            return []

    return findings(
        git(["diff", "--no-color", "--no-ext-diff", "-U0", "-M"] + diff_args, cwd, env),
        git(["diff", "--name-status", "-M"] + diff_args, cwd, env),
        lambda p: show(new_rev, p),
        lambda p: show(old_rev, p),
        listing,
    )

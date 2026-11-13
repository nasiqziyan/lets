#!/usr/bin/env bash
# Best-effort smoke test for Codex (Codex has no eval runner like `claude plugin eval`).
# Runs the same prompts as evals/plugin/ through `codex exec` in throwaway repos, applies a rough
# text check, and keeps every reply in $OUT so you can read them. Spends Codex usage: 4 short runs. guard-is-live needs the guard trusted once with /hooks.
# Usage: evals/codex-smoke.sh [model]
set -u
OUT="${OUT:-$(mktemp -d)}"; MODEL="${1:-}"
pass=0; fail=0
case_run() { # name, prompt, regex that should appear (extended grep), regex that must not appear ("" for none)
  local name="$1" prompt="$2" want="$3" deny="$4" dir="$OUT/$1"
  mkdir -p "$dir/repo"; git -C "$dir/repo" init -q
  codex exec -C "$dir/repo" --ephemeral --skip-git-repo-check ${MODEL:+-m "$MODEL"} -o "$dir/reply.md" "$prompt" >"$dir/log.txt" 2>&1
  if grep -Eqi "$want" "$dir/reply.md" && { [ -z "$deny" ] || ! grep -Eqi "$deny" "$dir/reply.md"; }; then
    pass=$((pass+1)); echo "  ok   $name"
  else
    fail=$((fail+1)); echo "  FAIL $name (read $dir/reply.md)"
  fi
}
case_run next-routes '$lets:next There is a typo in the footer: "Copyrite". What should I run?' 'lets:patch' 'lets:fix|lets:commit-message'
case_run change-start-needs-setup '$lets:change-start add-order-export Let shop owners download their orders as a CSV file.' 'lets setup' ''
case_run learn '$lets:learn debouncing' 'already know|familiar|\?' ''
case_run guard-is-live 'Run exactly this command and nothing else, then quote the exact output or error message you got: git commit --allow-empty --no-verify -m canary' 'lets guard' 'root-commit|committed successfully'
echo "$pass passed, $fail failed. Replies: $OUT"
[ "$fail" -eq 0 ]

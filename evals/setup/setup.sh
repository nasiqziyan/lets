#!/usr/bin/env bash
# Runs before each scenario (claude plugin eval --scaffold): installs LETS into the run's home and makes a small
# sample repo, set up for LETS, in the empty workspace. @LETS@ is filled in by `scripts/maint.py evals`.
set -euo pipefail
L="@LETS@"
export PATH="$HOME/.lets-package/node_modules/.bin:$PATH" LETS_NO_UPDATE_CHECK=1
export GIT_AUTHOR_NAME=dev GIT_AUTHOR_EMAIL=dev@example.com GIT_COMMITTER_NAME=dev GIT_COMMITTER_EMAIL=dev@example.com
cp -R "$L" "$HOME/.lets-package"
"$HOME/.lets-package/bin/lets" install --yes >/dev/null
git init -q -b main .
mkdir -p src
cat > package.json <<'J'
{ "name": "shop", "private": true, "scripts": { "check": "node --test" } }
J
cat > src/orders.js <<'J'
// Orders: list a customer's orders.
export function listOrders(db, customerId) {
  return db.orders.filter((o) => o.customerId === customerId);
}
J
printf '# Shop\n\nA small online shop.\n' > README.md
git add -A && git commit -qm "Start the shop"
"$HOME/lets/bin/lets" setup --yes --mode one --path . --planning in-repo --check 'npm run -s check' >/dev/null
git add -A && git commit -qm "Set up plans" >/dev/null 2>&1 || true

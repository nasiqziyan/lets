set -e
(cd plans && openspec new change add-order-export >/dev/null)
printf '## Why\n\nExport orders.\n\n## What Changes\n\n- A CSV export of orders.\n' > plans/openspec/changes/add-order-export/proposal.md
printf '## 1. Export button\n\n- [ ] 1.1 Add the button\n' > plans/openspec/changes/add-order-export/tasks.md
git add -A && git commit -qm "Plan add-order-export"

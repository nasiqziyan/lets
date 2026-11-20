# An open change, to be dropped.
(cd plans && openspec new change try-dark-mode >/dev/null)
printf '## Why\n\nTry a dark theme.\n\n## What Changes\n\n- A dark theme for the shop.\n' > plans/openspec/changes/try-dark-mode/proposal.md
git add -A && git commit -qm "Plan try-dark-mode"

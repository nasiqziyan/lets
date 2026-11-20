# An open change with a proposed spec change, to be dropped. Fails loudly if the fixture isn't there.
set -e
(cd plans && openspec new change try-dark-mode >/dev/null)
printf '## Why\n\nTry a dark theme.\n\n## What Changes\n\n- A dark theme for the shop.\n' > plans/openspec/changes/try-dark-mode/proposal.md
mkdir -p plans/openspec/changes/try-dark-mode/specs/theme
printf '## ADDED Requirements\n\n### Requirement: Dark theme\nThe shop SHALL offer a dark theme.\n\n#### Scenario: Switching\n- **WHEN** a customer picks dark\n- **THEN** the shop shows the dark theme\n' > plans/openspec/changes/try-dark-mode/specs/theme/spec.md
test -f plans/openspec/changes/try-dark-mode/proposal.md
git add -A && git commit -qm "Plan try-dark-mode"

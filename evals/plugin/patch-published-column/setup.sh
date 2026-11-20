set -e
printf '// Orders export: a CSV that our partners import every night.\nexport const header = ["order_id", "total"];\n' > src/export.js
printf '\n## Orders export\n\nPartners import the nightly orders CSV; its columns are part of our agreement with them.\n' >> README.md
git add -A && git commit -qm "Orders export"

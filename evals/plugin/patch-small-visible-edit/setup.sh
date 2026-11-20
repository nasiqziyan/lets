set -e
printf '// The orders page.\nexport const buyButton = { label: "Buy", action: "addToBasket" };\n' > src/page.js
git add -A && git commit -qm "Orders page"

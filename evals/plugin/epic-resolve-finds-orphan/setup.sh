E=plans/epics/shop-checkout; mkdir -p $E/prerequisites plans/research
printf '# shop-checkout\n\n## Destination\nAn overview, then the changes.\n\n## Decisions so far\n\n## Not yet specified\n\n## Out of scope\n' > $E/map.md
printf '# 01: What should the basket keep?\nType: grilling\nStatus: open\nWaits on: none\n\n## Question\nWhat the basket keeps between visits.\n' > $E/prerequisites/01-basket.md
printf '# 02: What do card providers charge?\nType: research\nStatus: claimed\nWaits on: none\n\n## Question\nFees of the main card providers.\n' > $E/prerequisites/02-provider-fees.md
printf '# Card provider fees\n\nPayfast 1.4%% + 20p; Cardline 1.5%%.\n' > plans/research/card-provider-fees.md
git add -A && git commit -qm "Chart shop-checkout"

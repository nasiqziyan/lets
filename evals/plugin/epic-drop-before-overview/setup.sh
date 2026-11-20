set -e
E=plans/epics/shop-checkout; mkdir -p $E/prerequisites plans/research
printf '# shop-checkout\n\n## Destination\nAn overview, then the changes.\n\n## Decisions so far\n- [01: What do card providers charge?](prerequisites/01-provider-fees.md): more than the margin on most orders.\n\n## Not yet specified\n\n## Out of scope\n' > $E/map.md
printf '# 01: What do card providers charge?\nType: research\nStatus: resolved\nWaits on: none\n\n## Answer\nFees are more than the margin on most orders. Findings: [card-provider-fees](../../../research/card-provider-fees.md)\n' > $E/prerequisites/01-provider-fees.md
printf '# Card provider fees\n\nPayfast 1.4%% + 20p; Cardline 1.5%%.\n' > plans/research/card-provider-fees.md
git add -A && git commit -qm "Chart shop-checkout"

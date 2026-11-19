E=plans/epics/shop-checkout; mkdir -p $E/prerequisites $E/inputs
cat > $E/map.md <<'M'
# shop-checkout

## Destination
An overview of checkout, then the changes that deliver it.

## Decisions so far
- [01: Which payment provider?](prerequisites/01-which-provider.md): Payfast.

## Not yet specified
- Refunds.

## Out of scope
M
printf '# 01: Which payment provider?\nType: grilling\nStatus: resolved\nWaits on: none\n\n## Question\nWhich provider?\n\n## Answer\nPayfast.\n' > $E/prerequisites/01-which-provider.md
printf '# 02: Confirm what Payfast supports\nType: action\nStatus: open\nWaits on: 01\n\n## Question\nAsk Payfast which payment methods we can take.\n' > $E/prerequisites/02-confirm-methods.md
printf '# 03: Where do the pull requests split?\nType: grilling\nStatus: open\nWaits on: 02\n\n## Question\nThe boundaries between the changes.\n' > $E/prerequisites/03-pr-split.md
git add -A && git commit -qm "Chart shop-checkout"

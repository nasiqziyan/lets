set -e
E=plans/epics/shop-checkout; mkdir -p $E/prerequisites
printf '# shop-checkout\n\n## Destination\nAn overview, then the changes.\n\n## Decisions so far\n- Card payments through Payfast.\n\n## Not yet specified\n\n## Out of scope\n' > $E/map.md
printf '# Shop checkout\n\n## User stories\n1. As a customer, I can pay by card.\n2. As a customer, I get an order email.\n\n## Delivery\n1. `take-card-payment`: take a card payment. Waits on: nothing.\n2. `email-order-confirmation`: email the order. Waits on: take-card-payment.\n' > $E/overview.md
git add -A && git commit -qm "Epic shop-checkout"

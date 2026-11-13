# Plan an epic (work bigger than one pull request)

Use the epic route when the work needs several pull requests and much is still undecided.

1. `/lets:epic-start shop-checkout` charts a map: where you're going, what's decided, and the open questions as
   numbered **prerequisites** (research, grilling, a prototype, or an action only you can take). Put source material
   in `plans/epics/shop-checkout/inputs/` first if you have any.
2. `/lets:epic-resolve shop-checkout` takes one ready prerequisite at a time, in a session of its own, and records the
   decision on the map. Repeat until nothing is open. It adds new prerequisites when it uncovers them.
3. `/lets:epic-overview shop-checkout` writes the overview: the document for people who weren't in the sessions. It
   ends with **Delivery**: the changes, one per pull request, in order.
4. Share the overview. When the team comments, `/lets:epic-revise shop-checkout` takes the comments one at a time.
5. `/lets:epic-split shop-checkout` turns the overview into those changes, checks that nothing is lost on the way, and
   lists them in the map's `## Changes` section. Then build each change as usual.

To stop an epic: `/lets:epic-revise shop-checkout --drop`. Its open changes are dropped with a reason.

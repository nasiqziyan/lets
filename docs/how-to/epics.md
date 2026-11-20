# Plan an epic (work bigger than one pull request)

Use the epic route when the work needs several pull requests and much is still undecided.

1. `/lets:epic-start shop-checkout` creates `plans/epics/shop-checkout/inputs/` and asks you to describe the work.
   Put any notes, specs or diagrams in that folder, or tell it where they are and it copies them in. Then it charts
   a map: where you're going, what's decided, and the open questions as numbered **prerequisites** (research,
   grilling, a prototype, or an action only you can take). Research starts in the background while you talk.
2. `/lets:epic-resolve shop-checkout 01` resolves one prerequisite and records the decision on the map. It adds new
   prerequisites when it uncovers them. Every step ends with what's ready and the next command; run that in a fresh
   session (`/clear` or a new tab), and repeat until nothing is open.

   Research needs nothing from you, so it can run in another tab while you work on something else:
   `/lets:epic-resolve shop-checkout research` starts every ready research prerequisite. If a step says research is
   still running, start the next step in a new tab and leave that one open: it records the research as it finishes.
3. `/lets:epic-overview shop-checkout` writes the overview: the document for people who weren't in the sessions. It
   ends with **Delivery**: the changes, one per pull request, in order.
4. Share the overview. When the team comments, `/lets:epic-revise shop-checkout` takes the comments one at a time.
5. `/lets:epic-split shop-checkout` turns the overview into those changes, checks that nothing is lost on the way, and
   lists them in the map's `## Changes` section. Then build each change as usual.

To stop an epic: `/lets:epic-revise shop-checkout --drop`. Its open changes are dropped with a reason.

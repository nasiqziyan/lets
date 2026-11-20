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
   ends with **Delivery**: it proposes the changes, one per pull request, in order, and settles the list with you, so
   the team reviews how the work is delivered along with the rest.
4. Share the overview. When the team comments, `/lets:epic-revise shop-checkout` reads the comments on the planning
   pull request (or takes the ones you give it) and goes through them one at a time.
5. `/lets:epic-split shop-checkout` turns the overview into those changes, checks that nothing is lost on the way, and
   lists them in the map's `## Changes` section. Then build each change as usual.

To stop an epic, at any point (before its overview too): `/lets:epic-revise shop-checkout --drop`, or tell
`/lets:epic-resolve` to drop it when a finding shows it isn't worth doing. Its open changes are dropped with a reason,
recorded on the map.

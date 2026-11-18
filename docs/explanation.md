# How LETS works, and why

## The unit is the change

A **change** is one pull request: a proposal, the requirements it adds or alters (with scenarios that say how to
prove each one), and its **tasks**, each a thin vertical slice built in one session. Changes come from
[OpenSpec](https://github.com/Fission-AI/OpenSpec); when a change closes, its requirements merge into the **living
specs**, which say how the system behaves now.

Work too big for one pull request is an **epic**: a map of decisions and open questions (prerequisites), resolved one
at a time, written up as an overview for people, then split into changes. The epic route is
[Matt Pocock's wayfinding](https://github.com/mattpocock/skills), with the epic's files as its tracker.

Work that changes no behaviour is a **patch**, and has no plan at all.

## Pairing by default

LETS assumes you want to understand, and could defend, every line you ship. In pair mode you write the code; the agent
gives you the context, says what to write and why, and checks it. Agent mode is a choice per repo or per build. Either
way, the walkthrough before the pull request explains the change in the order the code runs and quizzes you on the
decisions and risks in it, and only you can record it as done.

## Gates the agent can't loosen

The guard runs on every agent command and edit. It keeps git as local as you choose, refuses edits that weaken a test
or a check, keeps AI mentions out of every repo, and keeps agents off a team's forge where the team hasn't agreed to them.

## Plans live where the team works

Plans are plain Markdown: in the repo's `plans/` folder when the team uses LETS, in a planning repo shared by the team
(or a group of repos), or in a private planning repo when the plans are yours alone. Separately, you say whether the
team has agreed to agents working in its repo. You can change either later.

## Small and quiet

LETS adds about 2,100 tokens to each session (its map and your profile), keeps its commands out of the agent's reach
until you type them, and changes nothing on your computer without showing you first.

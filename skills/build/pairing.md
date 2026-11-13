# Pair mode (the default way we build)

The goal: I understand, and could defend, every line we ship, and my hands learn to write it. You navigate, I drive.

For each slice of work:

1. **Context first.** In a few sentences, say where this slice sits: what it must do, which modules and calls it touches, and what the surrounding code already does. Point at the files and lines.
2. **Tell me what to write.** Say what I should write next and where, why it is shaped that way, and how it works (the call it makes, the data it moves, the case it guards). Show the shape in words or pseudocode, not the finished code. Then stop and let me write it.
3. **Check what I wrote.** Read my change. Say what is right, then what is wrong or missing, pointing at the exact lines, and why. Let me fix it myself. If it's right, say so in one line and move on.
4. **Hand-offs.** When I say "you write this" (a piece of boilerplate, a test fixture, a whole function), write that piece only, then tell me in two or three sentences what you wrote and why, and go back to pairing for the next piece.
5. **Raise the help one step at a time** when I'm stuck: a hint, then a pointed question, then a partial example, and only then the code, which I explain back to you.
6. **Grow the steps.** As I get things right, give me bigger pieces with less explanation. When a concept is new to me, start with one worked instance from this codebase and give me the next one.

Pace each message by my message length (my profile): split a long explanation across messages, never squeeze it. Don't stop where the only sensible reply is "continue":
stop when I have something to write, decide or answer. If something needs more than a few lines of teaching, don't teach it here: suggest a detour (`/branch` in Claude Code, `/fork` in Codex, then `/lets:learn <concept>` there; in Codex, `$lets:learn`).

**Agent mode** for this task when I say so ("agent mode", "you build this"): you write the code, then walk me through it slice by slice before we call it done. Pair mode comes back on the next task.

If you lose track of this protocol (after compaction, say), re-read this file: `~/lets/plugin/skills/build/pairing.md`.

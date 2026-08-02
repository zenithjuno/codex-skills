# Mode: normal (`grill-to-build`)

One question at a time. Linear. Fast momentum. This mode trades a little design completeness for speed; accept that a few edge cases may surface during the build rather than being designed away upfront.

All iron rules from SKILL.md still apply in full — never build before approval, lock decisions live, always recommend, two slugged contract artifacts, and the coding control plane when applicable.

## Cadence

- Ask **one** question per turn. Wait for the answer before the next.
- Each question carries: the options, a one-line trade-off per option, and **your recommendation with a brief reason**. Never a bare menu.
- For domain decisions, prefer **scenario-form** over abstract menus: "a student opens the game, skips question 3, and closes the tab — what should they see when they come back?" beats "should progress persist? A or B". A concrete situation from the user's own world pulls out their real ground truth far more reliably than option labels, and the answer routinely surfaces requirements no menu would have. Still attach your recommendation — stated as the outcome you'd expect, with the reason.
- After each answer, do two things in the *same* turn:
  1. **Lock it.** Append the decision to the running ledger (see below) and restate it in one line so the user sees it captured.
  2. **Ask the next question** — chosen by what most reduces remaining uncertainty.
- Prefer the question whose answer unblocks the most downstream decisions. Sequence from foundational (scope, model, core data shapes) to detailed (formatting, edge-case handling, polish).

## The running ledger (lightweight, but live — and on disk)

Maintain a visible, append-only list in the conversation. Minimal format:

```
PROBLEM  (locked first — the goal every decision serves; re-frame only via iron rule 6)
  - <the one-line current problem statement>
LOCKED
  - <decision 1>
  - <decision 2>
ASSUMPTIONS  (believed but not yet verified — each names its verification path)
  - <assumption — verify via: <a later question / a probe / a named build stage>>
OPEN (next up)
  - <the question currently on the table>
```

Keep it short — one line per decision. Checkpoint it to `GRILL-LEDGER-<short-slug>.md` in the chosen control home every few locks (~5), so the settled design survives a dead session — the chat is volatile; the file is not. At BLUEPRINT time the whole ledger migrates into the Decision Log (assumptions into the Assumptions section) and the checkpoint file is deleted. Nothing settled is ever held only in memory — or only in the chat.

## Knowing when to stop grilling

Stop and move to the BLUEPRINT when:
- The core model/approach is fixed, the main data/inputs and outputs are defined, and the obvious edge cases have a decided treatment; AND
- New questions are returning diminishing returns (cosmetic, or safely deferrable to the build).

Before that final check, run a **coverage sweep** — a fast pass over the categories grills systematically under-ask, because no user answer naturally spawns them: (a) the **maintenance story** — how the user will update content/data later, alone, without you; (b) **failure behavior** — what the artifact's user sees when something goes wrong; (c) **definition of done** — the end-to-end acceptance check for the whole project, agreed now rather than discovered at the last gate; (d) **non-functional constraints** — offline use, low-spec devices, mobile screens, printing; (e) **other hands** — who besides the user touches the inputs or outputs. Ask only where nothing is locked yet; skip what's covered. Also confirm every ASSUMPTIONS entry has a verification path — an assumption with none is an open question wearing a disguise.

Then do the quick sweep: *"Here's everything locked. Anything feel unresolved or wrong before I write it up?"*

## When a late answer contradicts an earlier lock

Say so explicitly, show the conflict, and ask which wins. Then update the ledger. This is iron rule 4 in action — you hold the whole design, so you must catch the collisions the user can't. If the contradicting answer actually re-frames the *problem itself* (not a peer decision), use the re-lock gate from iron rule 6 — confirm old → new with the reason — rather than treating it as an ordinary conflict.

## Then

The slug, control home, project root/path roles, and VCS strategy were fixed at the start (iron rule 5). Write `BLUEPRINT-<short-slug>.md` with the canonical Task Contract (see `references/blueprint-format.md`), run its **fidelity gate** (self-audit the ledger migration and coding Active Contract Index, then the user sweeps the Decision Log and confirms), then write `CONSTRUCTION_PLAN-<short-slug>.md` (see `references/construction-plan-format.md`). For coding, create the bounded BUILD-CONTROL beside them and merge its exact pointer block into AGENTS.md. Then **stop at the approval gate**.

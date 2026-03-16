# MADR Section Guide

## Section overview

| Section | Required? | adg manages? | Notes |
|---|---|---|---|
| YAML front matter (`status`, `date`, `decision-makers`) | No | Partially | adg sets `status: decided`; `date` and `decision-makers` require direct edit |
| Context and Problem Statement | Yes | Yes — `adg edit --question` | 2-3 sentences describing the situation and the question |
| Decision Drivers | No | Header only | Bullet list of forces/constraints motivating the decision; edit file directly |
| Considered Options | Yes | Yes — `adg edit --option` | One title per option; detailed pros/cons go in a separate section |
| Decision Outcome | Yes | Yes — `adg decide` | "Chosen option: X, because Y" format |
| Consequences | No | No | Good/bad bullet list under Decision Outcome; edit file directly |
| Confirmation | No | No | How to verify compliance; valuable for enforcement-heavy decisions |
| Pros and Cons of the Options | No | No | Detailed argument per option; edit file directly after adg completes |
| More Information | No | No | Cross-model refs, context, links to issues; edit file directly |

## What goes in each section

**Context and Problem Statement** — Describe the situation in 2-3 sentences. End with the question being decided. Example: "The workflow needs to communicate with the host platform. Calls cannot be direct due to the iframe boundary. How should the workflow send commands and receive responses?"

**Decision Drivers** — Bullet list of forces: constraints, quality attributes, concerns that shaped the decision. These are NOT criteria for scoring options — they're the pressures you faced. Example: `* Must work across browsers without native postMessage quirks` / `* Must be testable without a live Eyra host`.

**Considered Options** — Just titles at this level. The detailed arguments go in "Pros and Cons of the Options" below. Keep titles concise: "FakeBridge / LiveBridge abstraction", "Direct postMessage calls", "Global event bus".

**Decision Outcome** — "Chosen option: X, because {single sentence connecting the choice to a decision driver}." Be specific: not "because it's best" but "because it allows the same workflow code to run in dev (FakeBridge) and production (LiveBridge) without modification."

**Consequences** — What changes as a result. Be honest about trade-offs.
- Good: `* Dev server works without Eyra host`
- Bad: `* Bridge interface must be kept stable across framework versions`

**Confirmation** — How will compliance be verified? "Code review flags any direct postMessage calls outside LiveBridge." or "Pyright enforces the type contract." This section makes enforcement explicit.

**Pros and Cons of the Options** — One subsection per option. Use the same titles as in Considered Options. Bullet format: `Good, because X` / `Neutral, because X` / `Bad, because X`.

**More Information** — Cross-model references (markdown links), related GitHub issues, links to relevant upstream decisions, or context that doesn't fit elsewhere.

## YAML front matter

```yaml
---
status: accepted
date: YYYY-MM-DD
decision-makers: Danielle McCool
---
```

`status` values: `proposed` | `accepted` | `deprecated` | `superseded by [ADR-NNNN](link)`

adg sets `status: decided` when you run `adg decide`. Update to `accepted` when finalised.
`date` is the date the decision was last updated (not created).

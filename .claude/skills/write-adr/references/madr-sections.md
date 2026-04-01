# MADR Section Guide

## Section overview

All content flows through adg commands. Never edit ADR markdown files directly.

| Section | Required? | adg command | Notes |
|---|---|---|---|
| YAML front matter | No | Managed by adg | `status`, `date`, tags, links — all via adg commands |
| Context and Problem Statement | Yes | `adg edit --question` | 2-3 sentences describing the situation and the question |
| Decision Drivers | No | `adg edit --criteria` | Each call appends to the section |
| Considered Options | Yes | `adg edit --option` | One title per option |
| Decision Outcome | Yes | `adg decide --option --rationale` | Only when a decision has been made |
| Pros and Cons of Options | No | `adg edit --criteria` | Appended after drivers under `### Pros and Cons` sub-header |
| Consequences | No | `--rationale` or `adg comment` | Include in rationale text, or add as a structured comment |
| More Information | No | `adg comment` | Cross-model refs, context, links to issues |

## What goes in each section

**Context and Problem Statement** — Describe the situation in 2-3 sentences. End with the question being decided. Example: "The workflow needs to communicate with the host platform. Calls cannot be direct due to the iframe boundary. How should the workflow send commands and receive responses?"

**Decision Drivers** — Added via `adg edit --criteria`. Each call appends text. Bullet list of forces: constraints, quality attributes, concerns that shaped the decision. These are NOT criteria for scoring options — they're the pressures you faced.

**Considered Options** — Just titles at this level. The detailed arguments go in "Pros and Cons" (also in the criteria section). Keep titles concise.

**Pros and Cons of Options** — Appended to the criteria section via `adg edit --criteria` under a `### Pros and Cons` sub-header. One subsection per option. Bullet format: `Good, because X` / `Neutral, because X` / `Bad, because X`.

**Decision Outcome** — Set via `adg decide --option "X" --rationale "Y"`. Only when a decision has been made. Include consequences in the rationale text.

**Consequences** — For brief consequences, include them in the `--rationale` string. For detailed consequences, use `adg comment`:
```bash
adg comment --model m --id 0001 --text "Consequences: Good: X. Bad: Y."
```

**More Information** — Added via `adg comment`. Cross-model references, related GitHub issues, links to upstream decisions, or context that doesn't fit elsewhere:
```bash
adg comment --model m --id 0001 --text "More Information: See fork-governance/AD0003. Related: issue #42."
```

## Status values

adg uses: `open` → `decided`
MADR convention: `proposed` → `accepted` → `deprecated` → `superseded by [ADR-NNNN](link)`

The `create_adr.py` script handles the mapping. Decisions without a chosen option stay `open`.

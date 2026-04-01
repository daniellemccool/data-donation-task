---
name: write-adr
description: >
  Create a new Architectural Decision Record (ADR) using the MADR
  format and adg tool. Use this skill whenever the user asks to record, document, or write an
  architectural decision, asks "should this be an ADR", wants to capture a design choice or
  rejected alternative, or is about to implement something where the rationale should be
  preserved. Also use proactively when completing a feature that introduced a significant
  architectural pattern not yet documented.
---

# write-adr — Create an ADR

Decisions are recorded in MADR format using `adg`. There are 6 decision models in this project.
All content flows through adg commands — **never edit ADR markdown files directly**.

## Workflow

### 1. Identify the right model

Read `references/models.md` for the full table. Quick guide:
- Upstream relationship / feldspar modifications → `fork-governance`
- Framework internals (bridge, worker, factories) → `feldspar`
- Custom UI components, study-specific UI → `data-collector`
- Python layer structure, import rules → `python-architecture`
- Per-platform extraction, validation, column naming → `extraction`
- Test strategy, mocking, CI → `testing`

### 2. Check for duplicates and related decisions

```bash
adg list --model docs/decisions/<model>
```

If a related decision exists, plan to link to it. If the decision already exists as a stub (from the initial set), populate it using `adg edit` and `adg decide` directly (see `references/adg-reference.md`).

### 3. Gather the decision content

Before running the script, have ready:
- **Title** — short, action-oriented. "Use X for Y" or "Separate X from Y". Not a question.
- **Question** — 2-3 sentences: context + what is being decided. See `references/madr-sections.md`.
- **Options** — 2+ options. Can be strings or objects with pros/cons (see spec format below).
- **Drivers** — (optional) list of decision driver strings
- **Decision** — (optional) which option was chosen. Empty = unresolved (status: open).
- **Rationale** — (optional) why this option was chosen. Include consequences here.
- **More info** — (optional) cross-model references, related files, context
- **Tags** — (optional) fine-grained labels within the model, e.g. `facebook`, `validation`
- **Links** — (optional) within-model only. `{"from": "0002", "to": "0003"}` means 0002 precedes 0003.

### 4. Run the script

Write a JSON spec file (e.g. `/tmp/adr_spec.json`) and run:

```bash
python .claude/skills/write-adr/scripts/create_adr.py /tmp/adr_spec.json
```

**Decided example** (all fields):
```json
{
  "model": "docs/decisions/extraction",
  "title": "Dutch column names in consent UI",
  "question": "DataFrame columns are shown directly to Dutch-speaking participants. What language should column headers use?",
  "drivers": [
    "Participants are Dutch-speaking",
    "No translation infrastructure for column names"
  ],
  "options": [
    {"title": "English column names", "pros_cons": ["Good, because consistent with code", "Bad, because participants can't read them"]},
    {"title": "Dutch column names", "pros_cons": ["Good, because participants understand them", "Bad, because code/data language mismatch"]},
    "Bilingual via Translatable"
  ],
  "decision": "Dutch column names",
  "rationale": "Columns are rendered directly without translation infrastructure, so Dutch is necessary for participant comprehension.",
  "more_info": "See extraction/AD0001 for the flow template that renders these columns.",
  "tags": ["column-naming", "consent-ui"],
  "links": []
}
```

**Unresolved example** (no decision yet):
```json
{
  "model": "docs/decisions/feldspar",
  "title": "Migrate file delivery from WORKERFS to PayloadFile",
  "question": "How should the worker transition file delivery while maintaining backwards compatibility?",
  "drivers": ["Memory safety for large DDPs", "Backwards compatibility with researcher forks"],
  "options": [
    {"title": "Revert to WORKERFS", "pros_cons": ["Good, because scripts work", "Bad, because OOM on large files"]},
    {"title": "PayloadFile only", "pros_cons": ["Good, because no OOM", "Bad, because breaks all forks"]},
    {"title": "Capability flag opt-in", "pros_cons": ["Good, because gradual migration", "Neutral, because adds negotiation"]}
  ],
  "tags": ["worker-protocol"],
  "links": []
}
```

The script uses only adg commands internally:
- `adg add` → create stub
- `adg edit --question` → context and problem statement
- `adg edit --option` → considered options
- `adg edit --criteria` → decision drivers + pros/cons (appended under `### Pros and Cons`)
- `adg decide` → decision outcome (only when decision is provided)
- `adg tag` → tags
- `adg link` → within-model links
- `adg comment` → more information

### 5. Cross-model references

Cross-model links go in the `more_info` field of the spec, which becomes an adg comment.
Use relative paths: `See fork-governance/AD0003 for the upstream alignment policy.`

Within-model links (precedence) use the `links` field and are managed by `adg link`.

## Reference files

- `references/models.md` — model descriptions and selection guidance
- `references/adg-reference.md` — adg command syntax and notes
- `references/madr-sections.md` — section-by-section content guidance and adg command mapping
- `assets/madr-template.md` — full MADR template

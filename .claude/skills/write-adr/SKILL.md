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
The script handles mechanical adg invocations; you handle content and cross-model references.

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

If a related decision exists, plan to link to it. If the decision already exists as a stub (from the initial set), use `create_adr.py` is not needed — populate it instead using `adg edit` and `adg decide` directly (see `references/adg-reference.md`).

### 3. Gather the decision content

Before running the script, have ready:
- **Title** — short, action-oriented. "Use X for Y" or "Separate X from Y". Not a question.
- **Question** — 2-3 sentences: context + what is being decided. See `references/madr-sections.md`.
- **Options** — 2+ option titles. Include the "do nothing" option when relevant.
- **Decision** — which option was chosen (exact title or 1-based number)
- **Rationale** — one sentence connecting the choice to the key constraint or driver.
- **Tags** — (optional) fine-grained labels within the model, e.g. `facebook`, `validation`
- **Links** — (optional) within-model only. `{"from": "0002", "to": "0003"}` means 0002 precedes 0003.

### 4. Run the script

Write a JSON spec file (e.g. `/tmp/adr_spec.json`) and run:

```bash
python .claude/skills/write-adr/scripts/create_adr.py /tmp/adr_spec.json
```

Example spec:
```json
{
  "model": "docs/decisions/extraction",
  "title": "Dutch column names in consent UI",
  "question": "DataFrame columns are shown directly to Dutch-speaking participants in the consent UI. What language should column headers use?",
  "options": [
    "English column names",
    "Dutch column names",
    "Bilingual via Translatable"
  ],
  "decision": "Dutch column names",
  "rationale": "Columns are rendered directly as DataFrame column names without translation infrastructure, so Dutch is necessary for participant comprehension.",
  "tags": ["column-naming", "consent-ui"],
  "links": []
}
```

The script outputs the created decision ID and file path, then reminds you what to add manually.

### 5. Enrich the decision file directly

The script populates: Context and Problem Statement, Considered Options, Decision Outcome.

Open the generated `AD<NNNN>-*.md` file and add:
- **Decision Drivers** — bullet list of forces (see `references/madr-sections.md`)
- **Consequences** — Good/Bad bullets under Decision Outcome
- **Confirmation** — how compliance is verified (valuable for enforcement-heavy decisions)
- **Pros and Cons of the Options** — detailed argument per option
- **More Information** — cross-model reference links (see below)

Also update the YAML front matter: change `status: decided` to `status: accepted`, add `date: YYYY-MM-DD`.

The MADR template is at `assets/madr-template.md` for reference.

### 6. Add cross-model references

Cross-model links go in `## More Information` as relative markdown links. Example:

```markdown
## More Information

See [fork-governance/AD0003](../fork-governance/AD0003-maintain-upstream-alignment-for-the-feldspar-package.md)
for the upstream alignment policy that motivates this rule.
```

Path: `../other-model/ADnnnn-title-with-dashes.md` (relative from the model directory).
Also add the reciprocal reference in the linked-to decision's file.

## Reference files

- `references/models.md` — model descriptions and selection guidance
- `references/adg-reference.md` — adg command syntax and notes
- `references/madr-sections.md` — section-by-section content guidance
- `assets/madr-template.md` — full MADR template

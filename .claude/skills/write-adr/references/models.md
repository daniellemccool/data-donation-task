# ADR Models

All models live under `docs/decisions/<model-name>/`.

## Model selection

| Model | Use when the decision is about... | Consulted when... |
|---|---|---|
| `fork-governance` | Fork identity, upstream relationship, package boundaries, release process, divergence justification | Evaluating whether to modify feldspar; syncing upstream; deciding where new code goes; changing release process |
| `feldspar` | Framework internals: bridge protocol, worker engine, type system, base UI components, factory mechanism | Contributing upstream to Eyra; extending the protocol; debugging bridge/worker issues |
| `data-collector` | Study-specific UI: custom prompt components, visualization, app composition, component design patterns | Adding UI features; designing new prompts or visualizations; deciding component patterns |
| `python-architecture` | Python layer structure, dependency direction, import rules, code placement, helper organization | Writing any Python code; adding helpers; modifying script.py; restructuring |
| `extraction` | Per-platform data: DDP structure, validation, extractor patterns, column naming, data presentation | Adding/modifying platforms; changing extraction logic; adjusting consent UI |
| `testing` | Test strategy, test data handling, mocking patterns, validation tooling, CI | Writing tests; changing test infrastructure; adding CI |

## When a decision could go in two models

The primary home is where it would be consulted most often during development:
- A decision about *why* a component belongs in data-collector (not feldspar) → `fork-governance` (upstream alignment policy)
- A decision about *how* to structure that component → `data-collector`
- A decision about Python import rules → `python-architecture` (not `extraction`, even if motivated by platform work)
- A decision about a per-platform DDP format → `extraction`

## Cross-model references

Cross-model links are NOT managed by adg. They go in the `## More Information` section of the decision file as relative markdown links:

```markdown
## More Information

See [fork-governance/AD0003](../fork-governance/AD0003-maintain-upstream-alignment-for-the-feldspar-package.md)
for the upstream alignment policy that motivates this rule.
```

Path convention: `../other-model/ADnnnn-title-with-dashes.md` (relative from the decision's model directory).

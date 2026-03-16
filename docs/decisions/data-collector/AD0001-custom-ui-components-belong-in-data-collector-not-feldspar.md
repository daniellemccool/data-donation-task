---
adr_id: "0001"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-13 13:31:22"
links:
    precedes: []
    succeeds: []
status: accepted
date: 2026-03-13
tags:
    - components
    - factory
    - customization
title: Custom UI components belong in data-collector not feldspar
---

## <a name="question"></a> Context and Problem Statement

The VU 2026 study needs UI components not present in upstream feldspar: FileInputMultiple, Questionnaire, ConsentFormViz, RetryPrompt, ErrorPage. Eyra's architecture designates data-collector as the researcher customization point. Should study-specific components be added to feldspar's prompt library or to data-collector?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Add components to feldspar's default prompt library
2. <a name="option-2"></a> Add components to data-collector with factories registered in App.tsx
3. <a name="option-3"></a> Create a separate component package

## <a name="criteria"></a> Decision Drivers

* Study-specific components are not appropriate for Eyra upstream — they are VU 2026-specific and would not be accepted
* Adding to feldspar would create upstream merge conflicts every time a new study component is needed
* Eyra's architecture explicitly provides data-collector as the customization layer; the factory mechanism is designed for this use case

## <a name="outcome"></a> Decision Outcome
We decided for [Option 2](#option-2) because: Eyra's hello_world example shows the pattern: data-collector is the study-specific application layer; feldspar is the framework consumed by any researcher. Adding study-specific components to feldspar would require upstream changes for every new study feature and violates the upstream alignment policy.

### Consequences

* Good: New study components can be added without touching feldspar at all
* Good: The pattern is consistent: every custom prompt has `src/components/<name>/types.ts + component.tsx + factory.tsx` in data-collector
* Bad: Factories must be explicitly registered in App.tsx; forgetting to register a factory means the component silently never renders

### Confirmation

Code review: any new prompt component must have its factory registered in `packages/data-collector/src/App.tsx`. No `PromptFactory` implementations should appear in `packages/feldspar/`.

### Evidence of violation

The `feat/facebook-ddp-error-handling` branch added `TextAreaFactory` to feldspar's default factory list instead of data-collector's App.tsx.

## More Information

See [fork-governance/AD0003](../fork-governance/AD0003-maintain-upstream-alignment-for-the-feldspar-package.md) for the upstream alignment policy that motivates this rule.
See [feldspar/AD0001](../feldspar/AD0001-factory-pattern-for-ui-extensibility.md) for the factory mechanism that makes this pattern work.

## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-03-13 13:31:22) Danielle McCool: marked decision as decided

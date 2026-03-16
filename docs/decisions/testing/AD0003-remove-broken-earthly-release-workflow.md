---
adr_id: "0003"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-16 16:46:26"
    - author: Danielle McCool
      comment: "2"
      date: "2026-03-16 16:46:26"
links:
    precedes: []
    succeeds: []
status: decided
tags:
    - ci
    - release
    - earthly
title: Remove broken Earthly release workflow
---

## <a name="question"></a> Context and Problem Statement

d3i-infra/data-donation-task has a release.yml + _build_release.yml CI pipeline that calls Earthly, but Earthly was removed from the repo years ago — the pipeline is dead code. Meanwhile, actual releases happen via local release.sh in researcher forks, which loops through platforms with VITE_PLATFORM. d3i-infra is a template repo: researchers fork it, customize scripts, and release from their forks. What should the release pipeline look like?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Remove broken workflows, keep release.sh
2. <a name="option-2"></a> Replace Earthly workflow with pnpm-based CI release
3. <a name="option-3"></a> Keep broken workflows as-is

## <a name="criteria"></a> Decision Drivers
d3i-infra is a template repo — the sample scripts are not deployed as-is
Actual releases happen in researcher forks, not at d3i-infra level
The existing _build_release.yml references Earthly which was removed (commit 065590ec), making the workflow broken
release.sh works and produces per-platform zips with VITE_PLATFORM, which is what SURF Research Cloud deployments need
gh-pages.yml already validates that the template builds successfully on push to master
### Pros and Cons

**Remove broken workflows, keep release.sh**
* Good, because removes dead code that misleads contributors
* Good, because release.sh already works for the actual use case (researcher forks)
* Good, because gh-pages.yml already validates the build at d3i-infra level
* Neutral, because no automated release artifacts at d3i-infra, but none are needed

**Replace Earthly workflow with pnpm-based CI release**
* Good, because automated release artifacts on GitHub
* Bad, because d3i-infra sample scripts are not deployed — artifacts have no consumer
* Bad, because adds CI complexity for a template repo

**Keep broken workflows as-is**
* Bad, because dead code confuses contributors
* Bad, because release.yml will fail if anyone triggers it


## <a name="outcome"></a> Decision Outcome
We decided for [Option 1](#option-1) because: The Earthly-based release pipeline has been broken since Earthly was removed. Since d3i-infra is a template repo where researchers fork and release from their own copies using release.sh, automated release CI at the template level would produce artifacts nobody deploys. gh-pages.yml already validates the build. Removing the dead workflows reduces confusion.

## <a name="comments"></a> Comments
<a name="comment-2"></a>2. (2026-03-16 16:46:26) Danielle McCool: More Information:
See feldspar/AD0003 for the PayloadFile decision that also touched the worker/build pipeline. The broken workflows are _build_release.yml (Earthly) and release.yml (calls _build_release.yml). Earthly was removed in d3i-infra commit 065590ec.

#!/usr/bin/env python3
"""
create_adr.py — Create an ADR in a model using adg, driven by a JSON spec.

All content flows through adg commands exclusively. No direct file editing.

Usage:
    python create_adr.py <spec.json>

spec.json fields:
    model      (required) Path to the decision model, e.g. docs/decisions/extraction
    title      (required) Short decision title
    question   (required) Context and Problem Statement text (1-3 sentences)
    options    (required) List of option specs — either strings (title only) or objects:
                          {"title": "...", "pros_cons": ["Good, because X", "Bad, because Y"]}
    drivers    (optional) List of decision driver strings
    decision   (optional) The chosen option — exact title string or 1-based number.
                          Empty or omitted = unresolved (status: proposed).
    rationale  (optional) Why this option was chosen (may include consequences)
    more_info  (optional) Free-text for references, cross-model links, related files
    tags       (optional) List of tag strings for within-model filtering
    links      (optional) List of {from: "NNNN", to: "NNNN"} within-model precedence links

Output:
    Prints the created decision ID and file path.
    Exits non-zero on any adg failure.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR running {' '.join(cmd)}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return (result.stdout + result.stderr).strip()


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    spec_path = Path(sys.argv[1])
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    with spec_path.open() as f:
        spec = json.load(f)

    required = ["model", "title", "question", "options"]
    missing = [k for k in required if k not in spec]
    if missing:
        print(f"ERROR: missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)

    model = spec["model"]
    title = spec["title"]
    options = spec["options"]

    # 1. Create the decision stub
    output = run(["adg", "add", "--model", model, "--title", title])
    print(output)

    m = re.search(r"\((\d+)\)", output)
    if not m:
        print(f"ERROR: could not extract decision ID from adg output: {output}",
              file=sys.stderr)
        sys.exit(1)
    decision_id = m.group(1)

    # 2. Context and Problem Statement
    run(["adg", "edit", "--model", model, "--id", decision_id,
         "--question", spec["question"]])

    # 3. Considered Options (extract titles from option specs)
    for opt in options:
        opt_title = opt["title"] if isinstance(opt, dict) else opt
        run(["adg", "edit", "--model", model, "--id", decision_id,
             "--option", opt_title])

    # 4. Decision Drivers (via --criteria)
    for driver in spec.get("drivers", []):
        run(["adg", "edit", "--model", model, "--id", decision_id,
             "--criteria", driver])

    # 5. Pros and Cons (appended to criteria section under sub-header)
    pros_cons_parts = []
    for opt in options:
        if isinstance(opt, dict) and opt.get("pros_cons"):
            pros_cons_parts.append(f"**{opt['title']}**")
            for item in opt["pros_cons"]:
                pros_cons_parts.append(f"* {item}")
            pros_cons_parts.append("")
    if pros_cons_parts:
        pros_cons_text = "### Pros and Cons\n\n" + "\n".join(pros_cons_parts)
        run(["adg", "edit", "--model", model, "--id", decision_id,
             "--criteria", pros_cons_text])

    # 6. Decision Outcome (if a decision has been made)
    decision = spec.get("decision", "")
    rationale = spec.get("rationale", "")
    if decision:
        run(["adg", "decide", "--model", model, "--id", decision_id,
             "--option", str(decision),
             "--rationale", rationale])

    # 7. Tags
    for tag in spec.get("tags", []):
        run(["adg", "tag", "--model", model, "--id", decision_id, "--tag", tag])

    # 8. Within-model links
    for link in spec.get("links", []):
        run(["adg", "link", "--model", model,
             "--from", str(link["from"]), "--to", str(link["to"])])

    # 9. More Information (via comment)
    more_info = spec.get("more_info", "")
    if more_info:
        run(["adg", "comment", "--model", model, "--id", decision_id,
             "--text", f"More Information:\n{more_info}"])

    # Report
    print(f"\nADR created: {model}/AD{decision_id.zfill(4)}-*.md")
    print(f"Decision ID: {decision_id}")
    print(f"Status: {'decided' if decision else 'open'}")


if __name__ == "__main__":
    main()

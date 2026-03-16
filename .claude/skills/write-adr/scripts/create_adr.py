#!/usr/bin/env python3
"""
create_adr.py — Create an ADR in a model using adg, driven by a JSON spec.

Usage:
    python create_adr.py <spec.json>

spec.json fields:
    model      (required) Path to the decision model, e.g. docs/decisions/extraction
    title      (required) Short decision title
    question   (required) Context and Problem Statement text (1-3 sentences)
    options    (required) List of option title strings (2+ options)
    decision   (required) The chosen option — exact title string or 1-based number
    rationale  (required) Why this option was chosen
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
from datetime import date
from pathlib import Path


def _today() -> str:
    return date.today().isoformat()


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

    required = ["model", "title", "question", "options", "decision", "rationale"]
    missing = [k for k in required if k not in spec]
    if missing:
        print(f"ERROR: missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)

    model = spec["model"]
    title = spec["title"]

    # 1. Add the decision stub
    output = run(["adg", "add", "--model", model, "--title", title])
    print(output)

    m = re.search(r"\((\d+)\)", output)
    if not m:
        print(f"ERROR: could not extract decision ID from adg output: {output}", file=sys.stderr)
        sys.exit(1)
    decision_id = m.group(1)

    # 1b. Advance initial status from adg's "open" to MADR's "proposed".
    # adg add writes status: open; MADR uses "proposed" for the initial state.
    model_path = Path(model)
    id_padded = decision_id.zfill(4)
    stub_matches = list(model_path.glob(f"AD{id_padded}-*.md"))
    if stub_matches:
        stub_file = stub_matches[0]
        stub_content = stub_file.read_text()
        stub_content = stub_content.replace("status: open", "status: proposed", 1)
        stub_file.write_text(stub_content)
        run(["adg", "rebuild", "--model", model])

    # 2. Set context and problem statement
    run(["adg", "edit", "--model", model, "--id", decision_id,
         "--question", spec["question"]])

    # 3. Add considered options
    for option in spec["options"]:
        run(["adg", "edit", "--model", model, "--id", decision_id, "--option", option])

    # 4. Record the decision outcome
    run(["adg", "decide", "--model", model, "--id", decision_id,
         "--option", str(spec["decision"]),
         "--rationale", spec["rationale"]])

    # 4b. Advance status from adg's "decided" to MADR's "accepted".
    # adg decide writes status: decided (adg's own vocabulary). MADR uses "accepted"
    # for the same terminal state. The --template MADR flag maps section headers only,
    # not status words, so we patch the frontmatter directly.
    model_path = Path(model)
    id_padded = decision_id.zfill(4)
    matches = list(model_path.glob(f"AD{id_padded}-*.md"))
    if matches:
        adr_file = matches[0]
        content = adr_file.read_text()
        content = content.replace("status: decided", "status: accepted", 1)
        content = content.replace("date: \"\"\n", f"date: {_today()}\n", 1)
        adr_file.write_text(content)
        run(["adg", "rebuild", "--model", model])

    # 5. Apply tags (optional)
    for tag in spec.get("tags", []):
        run(["adg", "tag", "--model", model, "--id", decision_id, "--tag", tag])

    # 6. Create within-model links (optional)
    for link in spec.get("links", []):
        run(["adg", "link", "--model", model,
             "--from", str(link["from"]), "--to", str(link["to"])])

    # Find the created file
    list_output = run(["adg", "list", "--model", model, "--format", "simple"], check=False)
    file_line = next((l for l in list_output.splitlines() if l.startswith(decision_id)), None)

    print(f"\nADR created: {model}/AD{decision_id}-*.md")
    print(f"Decision ID: {decision_id}")
    if file_line:
        print(f"Index entry: {file_line}")
    print("\nNext: edit the .md file to add Decision Drivers, Consequences, Confirmation,")
    print("      Pros and Cons of Options, and More Information (cross-model refs).")


if __name__ == "__main__":
    main()

# adg Command Reference

adg is configured for MADR via `~/.adgconfig.yaml`. The section header mappings are:
- `--question` → "Context and Problem Statement"
- `--option` → "Considered Options"
- `--criteria` → "Decision Drivers"
- `--outcome` (via `decide`) → "Decision Outcome"

## Commands used in create_adr.py

```bash
# Add a decision stub
adg add --model <path> --title "<title>"
# Output: "Decision <title> (NNNN) added successfully."

# Set context and problem statement
adg edit --model <path> --id <NNNN> --question "<text>"

# Add a considered option (repeat for each option)
adg edit --model <path> --id <NNNN> --option "<option title>"

# Record the decision outcome
adg decide --model <path> --id <NNNN> --option "<title or 1-based number>" --rationale "<why>"

# Add tags (optional, for within-model filtering)
adg tag --model <path> --id <NNNN> --tag <tag>

# Create a within-model precedence link (A precedes B)
adg link --model <path> --from <NNNN> --to <NNNN>
# Custom relationship:
adg link --model <path> --from <NNNN> --to <NNNN> --tag "invalidates" --reverse-tag "invalidated by"
```

## Other useful commands

```bash
# List decisions in a model
adg list --model <path>
adg list --model <path> --format simple   # compact
adg list --model <path> --tag <tag>       # filtered

# View full decision content
adg view --model <path> --id <NNNN>

# Validate model index matches files
adg validate --model <path>

# Rebuild index after manual file changes
adg rebuild --model <path>
```

## ID conventions

adg assigns IDs automatically starting at 0001. IDs are 4-digit zero-padded integers.
Pass IDs as the numeric string: `--id 0001` or `--id 1` (both work).
File names follow: `AD<NNNN>-<title-with-dashes>.md`

## Status vocabulary: adg vs MADR

adg and MADR use different words at each lifecycle stage:

| adg status | MADR equivalent | How to get there |
|---|---|---|
| `open` | `proposed` | `adg add` |
| `decided` | `accepted` | `adg decide` |

`adg set-config --template MADR` maps **section headers** only (Context and Problem Statement, Decision Drivers, etc.) — it does not change adg's internal status vocabulary. There are no `adg propose` or `adg accept` commands.

`create_adr.py` handles both translations automatically:
- after `adg add`: patches `status: open` → `status: proposed`
- after `adg decide`: patches `status: decided` → `status: accepted`
- both patch steps call `adg rebuild` to sync the index

If advancing status manually, edit the frontmatter directly and run `adg rebuild --model <path>`.

## Notes

- `adg decide --option` accepts either the exact option title string or a 1-based integer index.
- `adg edit --option` is additive — each call appends one option. Use multiple `--option` flags in one call to add several at once.
- Links are within-model only. Cross-model references go in `## More Information` (edit file directly).
- adg does not manage: Decision Drivers content (it only sets the header), Consequences, Confirmation, Pros and Cons of Options, More Information. These require direct file editing.

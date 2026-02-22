import difflib
import re
from dataclasses import dataclass


@dataclass
class Hunk:
    index: int
    original_code: str
    proposed_code: str
    start_line: int   # 1-based line in original where change starts
    end_line: int     # 1-based line in original where change ends (inclusive)
    char_count_proposed: int


def compute_edit_delta(old: str, new: str) -> str:
    """Return a unified diff string (with context) between old and new content."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_lines, lineterm=""))


def parse_hunks(original: str, proposed: str) -> list:
    """
    Parse changes between original and proposed into individual Hunk objects.

    Uses n=0 (no context lines) so each separate change block becomes its own
    hunk — mirroring the Cursor-style accept/reject flow where each suggestion
    is a discrete unit.

    NOTE: This is a scoring pipeline utility only. It is never called at
    request time. The scoring pipeline calls it offline in run_component3()
    after session end to populate chunk_decisions from the three snapshots:
        original_content  →  proposed_content  →  snapshot_final
    """
    orig_lines = original.splitlines(keepends=True)
    prop_lines = proposed.splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(orig_lines, prop_lines, n=0))
    if not diff_lines:
        return []

    hunks = []
    hunk_index = 0
    i = 0

    # Skip the --- / +++ file header lines
    while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
        i += 1

    while i < len(diff_lines):
        line = diff_lines[i]
        if not line.startswith("@@"):
            i += 1
            continue

        # Parse "@@ -start[,count] +start[,count] @@"
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if not m:
            i += 1
            continue

        orig_start = int(m.group(1))
        orig_count = int(m.group(2)) if m.group(2) is not None else 1
        # For pure insertions orig_count == 0; end < start signals "insert after start"
        orig_end = orig_start + orig_count - 1 if orig_count > 0 else orig_start

        i += 1
        removed = []
        added = []

        while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
            dl = diff_lines[i]
            if dl.startswith("-"):
                removed.append(dl[1:])
            elif dl.startswith("+"):
                added.append(dl[1:])
            i += 1

        original_code = "".join(removed)
        proposed_code = "".join(added)

        hunks.append(Hunk(
            index=hunk_index,
            original_code=original_code,
            proposed_code=proposed_code,
            start_line=orig_start,
            end_line=orig_end,
            char_count_proposed=len(proposed_code),
        ))
        hunk_index += 1

    return hunks

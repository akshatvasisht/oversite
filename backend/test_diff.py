from diff import compute_edit_delta, parse_hunks, Hunk


# --- compute_edit_delta ---

def test_edit_delta_is_valid_unified_diff():
    delta = compute_edit_delta("a = 1\n", "a = 2\n")
    assert "@@" in delta
    assert "-a = 1" in delta
    assert "+a = 2" in delta


def test_edit_delta_identical_returns_empty():
    assert compute_edit_delta("same\n", "same\n") == ""


def test_edit_delta_empty_to_content():
    delta = compute_edit_delta("", "hello\n")
    assert "+hello" in delta


def test_edit_delta_content_to_empty():
    delta = compute_edit_delta("hello\n", "")
    assert "-hello" in delta


def test_edit_delta_multiline():
    old = "def foo():\n    return 1\n"
    new = "def foo():\n    x = 2\n    return x\n"
    delta = compute_edit_delta(old, new)
    assert "@@" in delta
    assert "-    return 1" in delta
    assert "+    x = 2" in delta
    assert "+    return x" in delta


# --- parse_hunks (benchmark tests from implementation plan) ---

def test_identical_content_produces_no_hunks():
    assert parse_hunks("abc", "abc") == []


def test_diff_hunk_parsing():
    original = "def foo():\n    return 1\n"
    proposed = "def foo():\n    x = 2\n    return x\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 1
    assert hunks[0].start_line == 2
    assert "x = 2" in hunks[0].proposed_code


def test_multi_hunk_parsing():
    # Two separate change blocks separated by unchanged lines → two hunks
    original = "line1\nline2\nline3\nline4\nline5\n"
    proposed = "changed1\nline2\nline3\nline4\nchanged5\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 2
    assert "changed1" in hunks[0].proposed_code
    assert "changed5" in hunks[1].proposed_code


# --- additional coverage ---

def test_hunk_dataclass_fields():
    original = "def foo():\n    return 1\n"
    proposed = "def foo():\n    x = 2\n    return x\n"
    hunks = parse_hunks(original, proposed)
    h = hunks[0]
    assert h.index == 0
    assert isinstance(h.original_code, str)
    assert isinstance(h.proposed_code, str)
    assert isinstance(h.start_line, int)
    assert isinstance(h.end_line, int)
    assert h.char_count_proposed == len(h.proposed_code)


def test_hunk_index_increments():
    original = "a\nb\nc\nd\ne\n"
    proposed = "X\nb\nc\nd\nY\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 2
    assert hunks[0].index == 0
    assert hunks[1].index == 1


def test_pure_insertion():
    original = "line1\nline3\n"
    proposed = "line1\nline2\nline3\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 1
    assert "line2" in hunks[0].proposed_code
    assert hunks[0].original_code == ""


def test_pure_deletion():
    original = "line1\nline2\nline3\n"
    proposed = "line1\nline3\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 1
    assert "line2" in hunks[0].original_code
    assert hunks[0].proposed_code == ""


def test_char_count_proposed_is_accurate():
    original = "a\n"
    proposed = "hello world\n"
    hunks = parse_hunks(original, proposed)
    assert hunks[0].char_count_proposed == len("hello world\n")


def test_empty_original_to_new_file():
    hunks = parse_hunks("", "def foo():\n    return 1\n")
    assert len(hunks) == 1
    assert "def foo" in hunks[0].proposed_code
    assert hunks[0].original_code == ""


def test_hunk_start_and_end_line():
    # Change on line 3 only → start_line == end_line == 3
    original = "a\nb\nc\nd\n"
    proposed = "a\nb\nC\nd\n"
    hunks = parse_hunks(original, proposed)
    assert len(hunks) == 1
    assert hunks[0].start_line == 3
    assert hunks[0].end_line == 3

"""Standalone test — no DB imports. Copies the parser + noise-stripping logic directly."""
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test")

# --- Copied from progress_service.py ---

_BULLET_RE = re.compile(r'^\s*[-*\u2022]\s+(.+)', re.MULTILINE)

_PLATFORM_NOISE = {
    "cses", "atcoder", "leetcode", "codeforces", "codechef",
    "striver", "neetcode", "hackerrank", "hackerearth", "gfg",
    "geeksforgeeks", "interviewbit", "spoj",
}

def _strip_platform_noise(header):
    words = header.split()
    cleaned = [w for w in words if w.lower() not in _PLATFORM_NOISE]
    return " ".join(cleaned).strip()

def _parse_bullet_list(content):
    lines = content.strip().splitlines()
    if len(lines) < 2:
        return None
    bullet_indices = [i for i, line in enumerate(lines) if _BULLET_RE.match(line)]
    if not bullet_indices:
        return None
    groups = []
    current_header = None
    current_items = []
    for i, line in enumerate(lines):
        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            if current_header is None:
                current_header = ""
            current_items.append(bullet_match.group(1).strip())
        else:
            raw_header = line.strip().rstrip(':').strip()
            if not raw_header:
                continue
            cleaned_header = _strip_platform_noise(raw_header)
            if not cleaned_header:
                logger.info(f"[NOISE] Skipping: '{raw_header}'")
                continue
            if current_header is not None and current_items:
                groups.append({"header": current_header, "items": current_items})
            current_header = cleaned_header
            current_items = []
    if current_header is not None and current_items:
        groups.append({"header": current_header, "items": current_items})
    if not groups:
        return None
    return groups

# --- Copied from topic_extractor.py (just the alias for "graph") ---
def has_graph_topic(header):
    return bool(re.search(r'\bgraph\b', header.lower()))

# === TESTS ===

print("=" * 60)
print("TEST 1: Platform noise stripping")
print("=" * 60)
assert _strip_platform_noise("CSES Graph") == "Graph"
assert _strip_platform_noise("Atcoder") == ""
assert _strip_platform_noise("Striver DP") == "DP"
assert _strip_platform_noise("Codeforces Graphs") == "Graphs"
assert _strip_platform_noise("Pure Topic") == "Pure Topic"
print("  ALL PASS")

print()
print("=" * 60)
print("TEST 2: Main test case")
print("=" * 60)
test_msg = (
    "CSES Graph\n"
    " - Road Reparation\n"
    " - Road Construction\n"
    " Atcoder\n"
    " - Ladder Takahashi\n"
    " - Belt Conveyor"
)
groups = _parse_bullet_list(test_msg)
print(f"  Groups: {groups}")
assert len(groups) == 1, f"Expected 1 group, got {len(groups)}"
assert groups[0]["header"] == "Graph", f"Expected header 'Graph', got {groups[0]['header']!r}"
assert len(groups[0]["items"]) == 4, f"Expected 4 items, got {len(groups[0]['items'])}"
print(f"  Header: {groups[0]['header']!r}")
print(f"  Items:  {groups[0]['items']}")
print(f"  Count:  {len(groups[0]['items'])} == 4  PASS")

print()
print("=" * 60)
print("TEST 3: Two real topic headers")
print("=" * 60)
test_msg2 = (
    "Graphs\n"
    " - BFS\n"
    " - DFS\n"
    "Arrays\n"
    " - Two Sum\n"
)
groups2 = _parse_bullet_list(test_msg2)
print(f"  Groups: {groups2}")
assert len(groups2) == 2, f"Expected 2 groups, got {len(groups2)}"
assert groups2[0]["header"] == "Graphs"
assert len(groups2[0]["items"]) == 2
assert groups2[1]["header"] == "Arrays"
assert len(groups2[1]["items"]) == 1
print("  PASS")

print()
print("=" * 60)
print("TEST 4: Multiple noise headers, one topic")
print("=" * 60)
test_msg3 = (
    "CSES Graph\n"
    " - P1\n"
    "Atcoder\n"
    " - P2\n"
    "Codeforces\n"
    " - P3\n"
)
groups3 = _parse_bullet_list(test_msg3)
print(f"  Groups: {groups3}")
assert len(groups3) == 1, f"Expected 1 group, got {len(groups3)}"
assert len(groups3[0]["items"]) == 3, f"Expected 3 items, got {len(groups3[0]['items'])}"
print(f"  3 items under 1 group: PASS")

print()
print("ALL TESTS PASSED!")

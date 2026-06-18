"""Smoke test for the three bug fixes."""
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from utils.command_parser import parse_qdone, get_canonical_topic
from utils.topic_extractor import normalize_topic

print("=" * 60)
print("TASK 1 — Alias Mapping (normalize_topic)")
print("=" * 60)

alias_tests = [
    ("linkedlist", "Linked Lists"),
    ("ll", "Linked Lists"),
    ("linkedlists", "Linked Lists"),
    ("linked list", "Linked Lists"),
    ("slidingwindow", "Sliding Window"),
    ("sw", "Sliding Window"),
    ("sliding window", "Sliding Window"),
    ("twopointers", "Two Pointers"),
    ("2pointers", "Two Pointers"),
    ("two pointer", "Two Pointers"),
    ("binarysearch", "Binary Search"),
    ("dynamicprogramming", "Dynamic Programming"),
    ("arrays", "Arrays"),
    ("dp", "Dynamic Programming"),
]

all_pass = True
for raw, expected in alias_tests:
    result = normalize_topic(raw)
    status = "✅" if result == expected else "❌"
    if result != expected:
        all_pass = False
    print(f"  {status} normalize_topic('{raw}') → '{result}' (expected '{expected}')")

print()
print("=" * 60)
print("TASK 2 — get_canonical_topic via normalize_topic")
print("=" * 60)

canonical_tests = [
    ("linkedlist", "linked lists"),
    ("linked list", "linked lists"),
    ("ll", "linked lists"),
    ("slidingwindow", "sliding window"),
    ("sw", "sliding window"),
    ("twopointers", "two pointers"),
    ("2pointers", "two pointers"),
    ("arrays", "arrays"),
    ("dp", "dynamic programming"),
    ("binarysearch", "binary search"),
    ("bogus_topic", None),
]

for raw, expected in canonical_tests:
    result = get_canonical_topic(raw)
    status = "✅" if result == expected else "❌"
    if result != expected:
        all_pass = False
    print(f"  {status} get_canonical_topic('{raw}') → {result!r} (expected {expected!r})")

print()
print("=" * 60)
print("TASK 2 — parse_qdone (greedy multi-word topics)")
print("=" * 60)

qdone_tests = [
    ("!qdone linkedlist 1", [("linked lists", 1, None, "linkedlist 1")]),
    ("!qdone linked list 3", [("linked lists", 3, None, "linked list 3")]),
    ("!qdone ll 2 hard", [("linked lists", 2, "Hard", "ll 2 hard")]),
    ("!qdone arrays 5", [("arrays", 5, None, "arrays 5")]),
    ("!qdone sliding window 2", [("sliding window", 2, None, "sliding window 2")]),
    ("!qdone slidingwindow 4", [("sliding window", 4, None, "slidingwindow 4")]),
    ("!qdone sw 3 medium", [("sliding window", 3, "Medium", "sw 3 medium")]),
    ("!qdone binary search 2", [("binary search", 2, None, "binary search 2")]),
    ("!qdone dp 1", [("dynamic programming", 1, None, "dp 1")]),
    ("!qdone twopointers 1", [("two pointers", 1, None, "twopointers 1")]),
    ("!qdone 2pointers 3", [("two pointers", 3, None, "2pointers 3")]),
]

for cmd, expected in qdone_tests:
    try:
        result = parse_qdone(cmd)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_pass = False
            print(f"  {status} parse_qdone('{cmd}')")
            print(f"       got:      {result}")
            print(f"       expected: {expected}")
        else:
            print(f"  {status} parse_qdone('{cmd}') → {result[0][0]} qty={result[0][1]}")
    except Exception as e:
        all_pass = False
        print(f"  ❌ parse_qdone('{cmd}') raised: {e}")

# Test that invalid topics still raise ValueError
try:
    parse_qdone("!qdone bogustopic 1")
    all_pass = False
    print("  ❌ parse_qdone('!qdone bogustopic 1') should have raised ValueError")
except ValueError as e:
    print(f"  ✅ parse_qdone('!qdone bogustopic 1') correctly raised ValueError: {e}")

print()
print("=" * 60)
if all_pass:
    print("ALL TESTS PASSED ✅")
else:
    print("SOME TESTS FAILED ❌")
print("=" * 60)

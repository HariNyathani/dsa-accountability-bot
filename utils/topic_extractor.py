"""
Keyword-based topic extractor.

Scans a message for known DSA topics and returns a comma-separated list.
"""

import re
from typing import Dict, List, Tuple

STRICT_CANONICAL_TOPICS = [
    'Arrays', 'Strings', 'Linked Lists', 'Stacks', 'Queues', 'Hashing', 
    'Recursion', 'Sorting', 'Binary Search', 'Trees', 'Heaps', 'Graphs', 
    'Dynamic Programming', 'Greedy', 'Bit Manipulation', 'Math', 'Tries', 
    'Segment Trees', 'Disjoint Set', 'SQL', 'System Design',
    'Two Pointers', 'Sliding Window', 'Prefix Sum', 'Backtracking', 'Matrix', 'Divide and Conquer'
]

def normalize_topic(raw_topic: str) -> str:
    """Normalize pluralization and LeetCode naming conventions to our canonical names."""
    mapping = {
        # Sorting variants
        "sort": "Sorting",
        "sorting": "Sorting",
        "quick sort": "Sorting",
        "quicksort": "Sorting",
        "merge sort": "Sorting",
        "mergesort": "Sorting",
        "heap sort": "Sorting",
        "bubble sort": "Sorting",
        "insertion sort": "Sorting",
        "selection sort": "Sorting",
        "counting sort": "Sorting",
        "radix sort": "Sorting",
        # Singulars / LeetCode names
        "string": "Strings",
        "array": "Arrays",
        "linked list": "Linked Lists",
        "hash table": "Hashing",
        "hash map": "Hashing",
        "hashmap": "Hashing",
        "hashtable": "Hashing",
        "stack": "Stacks",
        "queue": "Queues",
        "tree": "Trees",
        "graph": "Graphs",
        "dp": "Dynamic Programming",
        "dynamic programming": "Dynamic Programming",
        "bfs": "Graphs",
        "dfs": "Graphs",
        "heap": "Heaps",
        "priority queue": "Heaps",
        "trie": "Tries",
        "binary search": "Binary Search",
        "two pointer": "Two Pointers",
        "sliding window": "Sliding Window",
        "prefix sum": "Prefix Sum",
        "divide and conquer": "Divide and Conquer",
        "bit manipulation": "Bit Manipulation",
        "backtracking": "Backtracking",
        "segment tree": "Segment Trees",
        "union find": "Disjoint Set",
        "disjoint set": "Disjoint Set",
        "matrix": "Matrix",
        "greedy": "Greedy",
        "recursion": "Recursion",
        "math": "Math",
        "maths": "Math",
    }
    cleaned = raw_topic.strip()
    return mapping.get(cleaned.lower(), cleaned.title())


# Aliases for free-text extraction: maps keyword -> canonical topic
# This allows "quick sort", "merge sort", singular forms, etc. to match canonical names
_EXTRACTION_ALIASES: Dict[str, str] = {
    # Sorting variants
    "sort": "Sorting",
    "sorting": "Sorting",
    "quick sort": "Sorting",
    "quicksort": "Sorting",
    "merge sort": "Sorting",
    "mergesort": "Sorting",
    "heap sort": "Sorting",
    "bubble sort": "Sorting",
    "insertion sort": "Sorting",
    "selection sort": "Sorting",
    "counting sort": "Sorting",
    "radix sort": "Sorting",
    # Singular -> Plural canonical mappings
    "array": "Arrays",
    "string": "Strings",
    "linked list": "Linked Lists",
    "stack": "Stacks",
    "queue": "Queues",
    "tree": "Trees",
    "graph": "Graphs",
    "heap": "Heaps",
    # Technique / concept aliases
    "dp": "Dynamic Programming",
    "bfs": "Graphs",
    "dfs": "Graphs",
    "priority queue": "Heaps",
    "hash map": "Hashing",
    "hashmap": "Hashing",
    "hash table": "Hashing",
    "hashtable": "Hashing",
    "trie": "Tries",
    "two pointer": "Two Pointers",
    "union find": "Disjoint Set",
    "segment tree": "Segment Trees",
    "maths": "Math",
}

# Provide TOPIC_PATTERNS for backwards compatibility with other modules, but make it strict.
TOPIC_PATTERNS: Dict[str, List[str]] = {
    canonical.lower(): [canonical.lower()] for canonical in STRICT_CANONICAL_TOPICS
}


def extract_topics(message: str) -> List[Tuple[str, int]]:
    """
    Return a list of (canonical_topic, count) tuples found in the message.
    Checks both STRICT_CANONICAL_TOPICS and _EXTRACTION_ALIASES (e.g. 'quick sort' -> 'Sorting').
    Longer aliases are matched first to avoid false partial matches.
    """
    text = message.lower()
    found: Dict[str, int] = {}

    # 1. Check aliases first (longest keyword first to avoid "sort" shadowing "quick sort")
    for keyword in sorted(_EXTRACTION_ALIASES.keys(), key=len, reverse=True):
        canonical = _EXTRACTION_ALIASES[keyword]
        pattern = r'(?:(\d+)\s+)?\b' + re.escape(keyword) + r'\b'
        for match in re.finditer(pattern, text):
            count_str = match.group(1)
            count = int(count_str) if count_str else 1
            if canonical not in found or count > found[canonical]:
                found[canonical] = count

    # 2. Check canonical topics directly (exact name match)
    for canonical in STRICT_CANONICAL_TOPICS:
        if canonical in found:
            continue  # already captured via alias
        canonical_lower = canonical.lower()
        pattern = r'(?:(\d+)\s+)?\b' + re.escape(canonical_lower) + r'\b'
        for match in re.finditer(pattern, text):
            count_str = match.group(1)
            count = int(count_str) if count_str else 1
            if canonical not in found or count > found[canonical]:
                found[canonical] = count

    return [(k, v) for k, v in found.items()]



def topics_to_str(topics: List[str]) -> str:
    """Join topics into a comma-separated string for DB storage."""
    return ", ".join(topics) if topics else ""

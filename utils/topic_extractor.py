"""
Keyword-based topic extractor.

Scans a message for known DSA topics and returns a comma-separated list.
"""

import re
from typing import Dict, List

# Canonical topics and their aliases / patterns
TOPIC_PATTERNS: Dict[str, List[str]] = {
    "arrays": ["array", "arrays", "subarray", "two pointer", "kadane"],
    "sliding window": ["slidingwindow", "sliding-window", "sliding window"],
    "strings": ["string", "strings", "substring", "anagram", "palindrome"],
    "linked lists": ["linked list", "linked lists", "singly linked", "doubly linked", "linkedlist"],
    "stacks": ["stack", "stacks", "monotonic stack"],
    "queues": ["queue", "queues", "deque", "priority queue"],
    "hashing": ["hash", "hashing", "hashmap", "hash map", "hash table", "hashtable", "hash set"],
    "recursion": ["recursion", "recursive", "backtracking", "backtrack"],
    "sorting": ["sorting", "sort", "merge sort", "quick sort", "bubble sort", "heap sort", "insertion sort", "selection sort"],
    "binary search": ["binary search", "bisect", "lower bound", "upper bound"],
    "trees": ["tree", "trees", "bst", "binary tree", "binary search tree", "avl", "red black"],
    "heaps": ["heap", "heaps", "min heap", "max heap", "priority queue"],
    "graphs": ["graph", "graphs", "bfs", "dfs", "dijkstra", "topological", "bellman", "floyd", "kruskal", "prim"],
    "dynamic programming": ["dynamic programming", "dp", "memoization", "tabulation", "knapsack", "lcs", "lis"],
    "greedy": ["greedy", "greedy algorithm"],
    "bit manipulation": ["bit manipulation", "bitwise", "bitmask", "xor"],
    "math": ["math", "number theory", "gcd", "lcm", "prime", "sieve", "modular arithmetic"],
    "tries": ["trie", "tries", "prefix tree"],
    "segment trees": ["segment tree", "segment trees", "fenwick", "bit tree"],
    "disjoint set": ["union find", "disjoint set", "dsu"],
    "sql": ["sql", "mysql", "postgres", "query", "join", "database query"],
    "system design": ["system design", "design pattern", "architecture"],
}


def extract_topics(message: str) -> List[str]:
    """
    Return a list of canonical topic names found in the message.
    Case-insensitive matching.
    """
    text = message.lower()
    found: List[str] = []

    for canonical, patterns in TOPIC_PATTERNS.items():
        for pattern in patterns:
            # word-boundary match
            if re.search(rf"\b{re.escape(pattern)}\b", text):
                if canonical not in found:
                    found.append(canonical)
                break  # no need to check more aliases for this topic

    return found


def topics_to_str(topics: List[str]) -> str:
    """Join topics into a comma-separated string for DB storage."""
    return ", ".join(topics) if topics else ""

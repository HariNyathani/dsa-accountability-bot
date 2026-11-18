"""
Unit tests for topic extraction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.topic_extractor import extract_topics


def _topic_counts(message: str) -> dict[str, int]:
    """Return the extractor's canonical-topic-to-count contract."""
    return dict(extract_topics(message))


def test_basic_topics():
    msg = "Today I studied arrays and solved 5 problems on linked lists"
    topics = _topic_counts(msg)
    assert topics == {"Arrays": 1, "Linked Lists": 1}


def test_dp_detection():
    msg = "Working on dynamic programming - knapsack problem"
    topics = _topic_counts(msg)
    assert topics == {"Dynamic Programming": 1}


def test_multiple_topics():
    msg = "Practiced BFS and DFS on graphs, then did some binary search problems"
    topics = _topic_counts(msg)
    assert topics == {"Binary Search": 1, "Graphs": 1}


def test_case_insensitive():
    msg = "RECURSION and Backtracking today"
    topics = _topic_counts(msg)
    assert topics == {"Recursion": 1, "Backtracking": 1}


def test_no_topics():
    msg = "Just reviewed some notes"
    topics = extract_topics(msg)
    assert topics == []


def test_sql_topic():
    msg = "Practiced SQL joins and subqueries"
    topics = _topic_counts(msg)
    assert topics == {"SQL": 1}


def test_plan_message():
    msg = "Plan: recursion and backtracking today"
    topics = _topic_counts(msg)
    assert topics == {"Recursion": 1, "Backtracking": 1}


def test_done_message():
    msg = "Done: binary search + 3 practice questions on trees"
    topics = _topic_counts(msg)
    assert set(topics) == {"Binary Search", "Trees"}


if __name__ == "__main__":
    test_basic_topics()
    test_dp_detection()
    test_multiple_topics()
    test_case_insensitive()
    test_no_topics()
    test_sql_topic()
    test_plan_message()
    test_done_message()
    print("✅ All topic extractor tests passed!")

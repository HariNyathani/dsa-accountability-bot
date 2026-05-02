"""
Unit tests for topic extraction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.topic_extractor import extract_topics


def test_basic_topics():
    msg = "Today I studied arrays and solved 5 problems on linked lists"
    topics = extract_topics(msg)
    assert "arrays" in topics
    assert "linked lists" in topics


def test_dp_detection():
    msg = "Working on dynamic programming - knapsack problem"
    topics = extract_topics(msg)
    assert "dynamic programming" in topics


def test_multiple_topics():
    msg = "Practiced BFS and DFS on graphs, then did some binary search problems"
    topics = extract_topics(msg)
    assert "graphs" in topics
    assert "binary search" in topics


def test_case_insensitive():
    msg = "RECURSION and Backtracking today"
    topics = extract_topics(msg)
    assert "recursion" in topics


def test_no_topics():
    msg = "Just reviewed some notes"
    topics = extract_topics(msg)
    assert len(topics) == 0


def test_sql_topic():
    msg = "Practiced SQL joins and subqueries"
    topics = extract_topics(msg)
    assert "sql" in topics


def test_plan_message():
    msg = "Plan: recursion and backtracking today"
    topics = extract_topics(msg)
    assert "recursion" in topics


def test_done_message():
    msg = "Done: binary search + 3 practice questions on trees"
    topics = extract_topics(msg)
    assert "binary search" in topics
    assert "trees" in topics


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

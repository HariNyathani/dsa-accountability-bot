import re
from typing import Dict, List, Optional, Tuple
from utils.topic_extractor import STRICT_CANONICAL_TOPICS, normalize_topic

# Pre-compute lowercase canonical set for fast membership checks
_CANONICAL_SET = {t.lower() for t in STRICT_CANONICAL_TOPICS}


def get_canonical_topic(raw_topic: str) -> Optional[str]:
    """Resolve a raw topic string to its canonical form.

    Uses normalize_topic() which handles all aliases (joined-word variants,
    shorthand codes, singular/plural, etc.).  Returns the *lowercase*
    canonical key if valid, or None if unrecognised.
    """
    normalized = normalize_topic(raw_topic)
    if normalized.lower() in _CANONICAL_SET:
        return normalized.lower()
    return None

DIFFICULTIES = {"easy", "medium", "hard"}

def parse_qdone(content: str) -> List[Tuple[str, int, Optional[str], str]]:
    """
    Parses `!qdone 5 arrays` or `!qdone arrays 2 hard` or `!qdone linked list 3`.

    Greedy topic matching: tries progressively longer word sequences against
    normalize_topic() to correctly identify multi-word topics like
    "linked list", "sliding window", "binary search", etc.

    Returns a list of tuples: (canonical_topic, count, difficulty, original_text_matched)
    """
    if content.lower().startswith("!qdone"):
        content = content[len("!qdone"):].strip()
    if not content:
        return []

    results = []
    chunks = [c.strip() for c in content.split(',')]
    
    for chunk in chunks:
        if not chunk: continue
        
        diff = None
        words = chunk.split()
        cleaned_words = []
        for w in words:
            if w.lower() in DIFFICULTIES:
                diff = w.title()
            else:
                cleaned_words.append(w)
                
        qty = None
        non_qty_words = []
        for w in cleaned_words:
            if w.isdigit():
                val = int(w)
                if val <= 0:
                    raise ValueError(f"Quantity must be a positive integer, got '{w}'")
                if qty is None:
                    qty = val
                else:
                    non_qty_words.append(w)
            else:
                # Check for float/decimal
                if '.' in w:
                    try:
                        float(w)
                        raise ValueError(f"Quantity must be a positive integer, got '{w}'")
                    except ValueError as e:
                        if "Quantity must be a positive integer" in str(e):
                            raise e
                non_qty_words.append(w)
                
        if qty is None:
            qty = 1

        # --- Greedy multi-word topic matching ---
        # Try the entire remaining string first, then shrink from the right.
        # This handles "linked list", "binary search", "divide and conquer", etc.
        canonical = None
        topic_str = " ".join(non_qty_words).strip()

        if topic_str:
            # First, try the full string as-is (handles both "linkedlist" and "linked list")
            canonical = get_canonical_topic(topic_str)

            if not canonical:
                # Try progressively shorter prefixes (greedy left-to-right)
                for length in range(len(non_qty_words), 0, -1):
                    candidate = " ".join(non_qty_words[:length])
                    result = get_canonical_topic(candidate)
                    if result:
                        canonical = result
                        break

        if not canonical:
            raise ValueError(f"Topic '{topic_str}' does not match any canonical topic. Use a valid topic like 'Arrays', 'Trees', etc.")
            
        results.append((canonical, qty, diff, chunk))
        
    return results

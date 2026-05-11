import re
from typing import Dict, List, Optional, Tuple
from utils.topic_extractor import TOPIC_PATTERNS

def get_canonical_topic(raw_topic: str) -> Optional[str]:
    raw_lower = raw_topic.lower().strip()
    for canonical, patterns in TOPIC_PATTERNS.items():
        if raw_lower == canonical:
            return canonical
        for pattern in patterns:
            if raw_lower == pattern.lower():
                return canonical
    return None

DIFFICULTIES = {"easy", "medium", "hard"}

def parse_qdone(content: str) -> List[Tuple[str, int, Optional[str], str]]:
    """
    Parses `!qdone 5 arrays` or `!qdone arrays 2 hard`.
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
        topic_words = []
        for w in cleaned_words:
            if w.isdigit():
                val = int(w)
                if val <= 0:
                    raise ValueError(f"Quantity must be a positive integer, got '{w}'")
                if qty is None:
                    qty = val
                else:
                    topic_words.append(w)
            else:
                # Check for float/decimal
                if '.' in w:
                    try:
                        float(w)
                        raise ValueError(f"Quantity must be a positive integer, got '{w}'")
                    except ValueError as e:
                        if "Quantity must be a positive integer" in str(e):
                            raise e
                topic_words.append(w)
                
        if qty is None:
            qty = 1
            
        topic_str = " ".join(topic_words).strip()
        canonical = get_canonical_topic(topic_str)
        if not canonical:
            raise ValueError(f"Topic '{topic_str}' does not match any canonical topic. Use a valid topic like 'Arrays', 'Trees', etc.")
            
        results.append((canonical, qty, diff, chunk))
        
    return results

def parse_plan_tomorrow(content: str) -> bool:
    """Returns True if this is a !plan tomorrow command."""
    lower = content.lower().strip()
    return lower.startswith("!plan tomorrow") or lower.startswith("!plan") and "tomorrow" in lower


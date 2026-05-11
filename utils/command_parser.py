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
    Parses `!qdone arrays 5 recursion 2` or `!qdone 2 sum 1` or `!qdone arrays 2 hard`.
    Returns a list of tuples: (canonical_topic, count, difficulty, original_text_matched)
    """
    if content.lower().startswith("!qdone"):
        content = content[len("!qdone"):].strip()
    elif content.lower().startswith("!qn"):
        content = content[len("!qn"):].strip()
    if not content:
        return []

    results = []

    if ',' in content:
        chunks = [c.strip().split() for c in content.split(',')]
    else:
        # No commas: heuristic space-separated parsing
        tokens = content.split()
        chunks = []
        current_chunk = []
        
        for token in tokens:
            token_lower = token.lower()
            is_num = token.isdigit()
            is_diff = token_lower in DIFFICULTIES
            
            terminal_found = False
            normal_seen = False
            for t in current_chunk:
                if not t.isdigit() and t.lower() not in DIFFICULTIES:
                    normal_seen = True
                elif normal_seen and (t.isdigit() or t.lower() in DIFFICULTIES):
                    terminal_found = True
                    
            if not is_num and not is_diff and terminal_found:
                chunks.append(current_chunk)
                current_chunk = [token]
            else:
                current_chunk.append(token)
                
        if current_chunk:
            chunks.append(current_chunk)
            
    for chunk in chunks:
        if not chunk: continue
        
        diff = None
        cleaned = []
        for t in chunk:
            if t.lower() in DIFFICULTIES:
                diff = t.title()
            else:
                cleaned.append(t)
                
        # If all cleaned tokens are digits (or empty), the difficulty word was actually the topic
        if all(t.isdigit() for t in cleaned):
            cleaned = chunk
            diff = None
            
        count = 1
        if len(cleaned) > 1 and cleaned[-1].isdigit():
            count = int(cleaned[-1])
            cleaned.pop()
            
        topic_str = " ".join(cleaned)
        canonical = get_canonical_topic(topic_str) or topic_str
        raw_str = " ".join(chunk)
        results.append((canonical, count, diff, raw_str))
        
    return results

def parse_plan_tomorrow(content: str) -> bool:
    """Returns True if this is a !plan tomorrow command."""
    lower = content.lower().strip()
    return lower.startswith("!plan tomorrow") or lower.startswith("!plan") and "tomorrow" in lower


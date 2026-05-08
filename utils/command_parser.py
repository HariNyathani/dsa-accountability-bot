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

def parse_qdone(content: str) -> List[Tuple[str, int, str]]:
    """
    Parses `!qdone arrays 5 recursion 2 sliding window 3`.
    Returns a list of tuples: (canonical_topic, count, original_text_matched)
    """
    content = content[len("!qdone"):].strip()
    
    # Split by numbers
    pattern = re.compile(r'(\d+)')
    parts = pattern.split(content)
    
    results = []
    current_text = ""
    
    # We expect text followed by a number. e.g. "arrays", "5", "recursion", "2"
    # Or number followed by text? "5 arrays". Let's handle standard "topic count".
    for part in parts:
        if part.strip() == "":
            continue
            
        if part.isdigit():
            count = int(part)
            # Strip typical separator characters that might accidentally be captured
            topic_str = current_text.strip(" \t-:=,;")
            if topic_str:
                canonical = get_canonical_topic(topic_str)
                if canonical:
                    results.append((canonical, count, topic_str))
                elif len(topic_str.split()) > 0:
                    # sometimes "dp 3 graphs" -> parts=..., "dp", "3", " graphs" -> current_text="graphs", next part="2"
                    # We might need a better heuristic, but simple text then number works if they separate it cleanly.
                    clean_last_word = topic_str.split()[-1].strip(" \t-:=,;")
                    canonical = get_canonical_topic(clean_last_word) # Try last word if multi-word unmatched
                    if not canonical and len(topic_str.split()) >= 2:
                        clean_last_two = " ".join(topic_str.split()[-2:]).strip(" \t-:=,;")
                        canonical = get_canonical_topic(clean_last_two)
                    if canonical:
                        results.append((canonical, count, topic_str))
            current_text = ""
        else:
            current_text += part
            
    return results

def parse_plan_tomorrow(content: str) -> bool:
    """Returns True if this is a !plan tomorrow command."""
    lower = content.lower().strip()
    return lower.startswith("!plan tomorrow") or lower.startswith("!plan") and "tomorrow" in lower


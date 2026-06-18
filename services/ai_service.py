"""
AI analysis service — optional insights using Google Gemini.

Only used when GEMINI_API_KEY is set. Otherwise, gracefully skips.
Supports both weekly analysis and on-demand insights per user.
"""

import logging
from typing import Optional
import config

logger = logging.getLogger("dsa_bot.ai")

_model = None


def _extract_text(response) -> Optional[str]:
    """Safely extract text from a Gemini response, with fallback paths."""
    try:
        text = response.text
        if text and text.strip():
            return text.strip()
    except Exception:
        pass

    try:
        candidates = response.candidates
        if candidates:
            parts = candidates[0].content.parts
            if parts:
                text = parts[0].text
                if text and text.strip():
                    return text.strip()
    except Exception:
        pass

    return "AI returned empty response."


def _get_model():
    global _model
    if _model is not None:
        return _model
    if not config.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-3.1-flash-lite")
        return _model
    except Exception as e:
        logger.error(f"Failed to initialise Gemini model: {e}")
        return None


async def analyse_progress(logs: list, streak_info: dict, consistency: float) -> Optional[str]:
    model = _get_model()
    if model is None:
        return None

    topics_list = []
    for log in logs:
        if log.get("topics"):
            topics_list.extend(log["topics"].split(", "))

    from collections import Counter
    topic_counts = Counter(topics_list)

    sample_lines = "\n".join(
        f'- [{l["log_date"]}] {l["message_content"][:120]}'
        for l in logs[:10]
    )

    prompt = f"""
You are a STRICT DSA performance analyzer.

Respond ONLY in short bullet points.

DATA:
- Streak: {streak_info['current_streak']}
- Consistency: {consistency:.1f}%
- Topics: {dict(topic_counts)}

Logs:
{sample_lines}

RULES:
- Max 100 words
- No intro text
- No motivation
- No explanations
- No repetition
- Bullet points only
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.7,
            },
        )
        return _extract_text(response)
    except Exception as e:
        print("Gemini Error:", e)
        logger.error(f"AI analysis failed: {e}")
        return "AI unavailable due to error."


async def generate_insights(logs: list, streak_info: dict, topic_summary: dict) -> Optional[str]:
    model = _get_model()
    if model is None or not logs:
        return None

    sample_lines = "\n".join(
        f'- [{l["log_date"]}] {l["message_content"][:150]}'
        for l in logs[-15:]
    )

    # FIXED: use topic_summary instead of undefined topic_counts
    top_topics = topic_summary.get("frequency", [])[:10]
    topics_text = ", ".join(f"{t}:{c}" for t, c in top_topics) if top_topics else "None"

    # FIXED: get consistency safely
    consistency = topic_summary.get("consistency", 0.0)

    # ✅ ONLY CHANGE: strict short prompt
    prompt = f"""
Analyze the DSA study data and respond ONLY in short, high-signal bullet points.

DATA:
- Streak: {streak_info['current_streak']}
- Messages: {len(logs)}
- Topics: {topics_text}

Logs:
{sample_lines}

OUTPUT:

Summary:
- topics count
- main topic
- diversity

Gaps:
- max 3 missing important topics

Focus:
- max 3 priorities (must be specific)

Next:
- max 3 concrete actions

RULES:
- Max 70 words
- No intro text
- No obvious statements (e.g., "streak is 1")
- No generic phrases
- No repetition
- Only bullet points
- Prioritize useful over complete
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.7,
            },
        )
        return _extract_text(response)
    except Exception as e:
        print("Gemini Error:", e)
        logger.error(f"AI insights failed: {e}")
        return "AI unavailable due to error."
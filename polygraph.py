"""
Module for Polygraph — a trust scorer for AI-generated code explanations.
Runs three checks (self-consistency, grounding, confidence) and produces
a 0-100 trust score with a verdict.
"""

import re
from typing import Dict, List

STOPWORDS: set = {
    "the", "is", "a", "this", "it", "of", "in", "to", "and", "for",
    "on", "that", "by", "with", "be", "are", "was", "were", "an",
    "at", "as", "its", "or", "but", "not", "from", "we", "they",
    "you", "he", "she", "will", "can", "has", "have", "do", "does",
    "did", "been", "being", "all", "each", "every", "no", "so",
    "if", "than", "then", "also", "just", "about", "up", "out",
    "their", "them", "these", "those", "some", "any"
}

HEDGE_WORDS: List[str] = [
    "might", "could", "possibly", "may", "perhaps", "unclear",
    "seems", "appears", "probably"
]

# Signal words for sentiment alignment check
# Alarm words: expected when risk is critical or high
SENTIMENT_ALARM: set = {
    "dangerous", "dangerously", "urgent", "urgently", "critical", "critically",
    "severe", "severely", "significant risk", "must", "immediately",
    "serious", "seriously", "unstable", "failure", "failures",
    "difficult", "risky", "fragile", "vulnerable", "prone", "hard to"
}
# Reassuring words: expected when risk is low
SENTIMENT_REASSURING: set = {
    "straightforward", "simple", "easy", "minor", "low risk",
    "manageable", "robust", "unlikely", "stable",
    "clear", "clean", "reliable", "safe", "low-risk",
    "trivial", "well-structured", "readable"
}


def _tokenize(text: str, exclude_terms: set = None) -> set:
    """Lowercases, extracts words, removes stopwords and optional exclude_terms, returns a set."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    result = {w for w in words if w not in STOPWORDS}
    if exclude_terms:
        result -= exclude_terms
    return result


def _word_overlap(a: str, b: str, exclude_terms: set = None) -> float:
    """Fraction of meaningful words common to both strings, with optional terms to exclude."""
    set_a = _tokenize(a, exclude_terms)
    set_b = _tokenize(b, exclude_terms)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _grounding_check(finding: dict, explanation: str) -> float:
    """Returns a 0-1 score: fraction of 4 facts mentioned in the explanation.
    
    Uses word-boundary regex matching so that "critical" does not match
    "critically", "low" does not match "below", and complexity "3" does
    not match "34". Missing or None facts count as 0 (not found).
    Denominator is always 4.
    """
    expl_lower = explanation.lower()
    facts_found = 0

    # Fact 1: function name
    func_name = finding.get("function")
    if func_name:
        if re.search(r"\b" + re.escape(str(func_name).lower()) + r"\b", expl_lower):
            facts_found += 1

    # Fact 2: file basename (last part of path, no dirs)
    file_path = finding.get("file")
    if file_path:
        file_basename = str(file_path).split("/")[-1].split("\\")[-1]
        # Keep word boundaries for the basename; re.escape handles the dot in .py
        if re.search(r"\b" + re.escape(file_basename.lower()) + r"\b", expl_lower):
            facts_found += 1

    # Fact 3: complexity as a standalone number
    complexity = finding.get("complexity")
    if complexity is not None and complexity != "":
        comp_str = str(complexity)
        if re.search(r"\b" + re.escape(comp_str) + r"\b", expl_lower):
            facts_found += 1

    # Fact 4: risk level word
    risk_level = finding.get("risk_level")
    if risk_level:
        rl_str = str(risk_level).lower()
        if re.search(r"\b" + re.escape(rl_str) + r"\b", expl_lower):
            facts_found += 1

    return facts_found / 4.0


def _confidence_check(explanation: str) -> float:
    """Returns a 0-100 score based on hedging language usage."""
    expl_lower = explanation.lower()
    count = 0
    for word in HEDGE_WORDS:
        # Count each occurrence of the hedge word as a standalone word
        matches = re.findall(r"\b" + re.escape(word) + r"\b", expl_lower)
        count += len(matches)
    return max(0.0, 100.0 - (count * 20.0))


def _check_sentiment_alignment(finding: dict, explanation: str) -> float:
    """Returns a 0-100 score: does the explanation's tone match the risk level?"""
    risk_level = str(finding.get("risk_level", "")).lower()
    expl_lower = explanation.lower()

    if risk_level in ("critical", "high"):
        expected_set = SENTIMENT_ALARM
        contradiction_set = SENTIMENT_REASSURING
    elif risk_level == "low":
        expected_set = SENTIMENT_REASSURING
        contradiction_set = SENTIMENT_ALARM
    else:
        # Moderate: no strong expected tone, score is neutral
        return 100.0

    # Count expected signal words (multi-word phrases checked first)
    expected_hits = 0
    for phrase in expected_set:
        if " " in phrase:
            if phrase in expl_lower:
                expected_hits += 1
        else:
            # Prefix-aware: match at word boundary start only, so "critical"
            # also matches "critically", "failure" matches "failures", etc.
            matches = re.findall(r"\b" + re.escape(phrase), expl_lower)
            expected_hits += len(matches)

    # Count contradiction signal words
    contradiction_hits = 0
    for phrase in contradiction_set:
        if " " in phrase:
            if phrase in expl_lower:
                contradiction_hits += 1
        else:
            # Prefix-aware match, same as above
            matches = re.findall(r"\b" + re.escape(phrase), expl_lower)
            contradiction_hits += len(matches)

    score = min(100.0, expected_hits * 25.0) - (contradiction_hits * 30.0)
    return max(0.0, score)


def score_explanation(finding: dict, explanation: str) -> dict:
    """
    Runs three trust checks on an AI-generated explanation.

    Args:
        finding: A function dict from the analyzer/scorer pipeline.
        explanation: The AI-generated explanation string.

    Returns:
        dict with keys: trust_score, consistency_score, grounding_score,
                         confidence_score, verdict, reason
    """
    # --- Guard: non-string or empty explanation ---
    if not isinstance(explanation, str) or not explanation.strip():
        return {
            "trust_score": 0.0,
            "consistency_score": 0.0,
            "grounding_score": 0.0,
            "sentiment_score": 0.0,
            "confidence_score": 0.0,
            "verdict": "FLAG",
            "reason": "No explanation was provided to score.",
        }

    # --- Check 1: Self-consistency (weight 0.20) ---
    from report_generator import explain_finding

    # Build a set of terms to exclude (function name, file name) so overlap isn't inflated
    func_name = str(finding.get("function", "")).lower()
    file_path = str(finding.get("file", ""))
    file_basename = file_path.split("/")[-1].split("\\")[-1].lower()
    exclude_terms = set()
    if func_name:
        exclude_terms.update(_tokenize(func_name))
    if file_basename:
        exclude_terms.update(_tokenize(file_basename))

    # Collect 4 explanations: the original + 3 new ones
    explanations = [explanation]
    for _ in range(3):
        try:
            explanations.append(explain_finding(finding))
        except Exception:
            explanations.append("")

    # Compare all 6 unique pairs
    pairs = [(i, j) for i in range(4) for j in range(i + 1, 4)]
    pairwise_scores: List[float] = []
    for i, j in pairs:
        if explanations[i] and explanations[j]:
            pairwise_scores.append(
                _word_overlap(explanations[i], explanations[j], exclude_terms) * 100.0
            )
        else:
            pairwise_scores.append(0.0)

    consistency_score = sum(pairwise_scores) / len(pairwise_scores) if pairwise_scores else 0.0

    # --- Check 2: Grounding (weight 0.30) ---
    grounding_raw = _grounding_check(finding, explanation)
    grounding_score = grounding_raw * 100.0

    # --- Check 3: Sentiment alignment (weight 0.35) ---
    sentiment_score = _check_sentiment_alignment(finding, explanation)

    # --- Check 4: Confidence (weight 0.15) ---
    confidence_score = _confidence_check(explanation)

    # --- Weighted average ---
    # Weights: consistency 20%, grounding 30%, sentiment 35%, confidence 15%
    trust_score = (
        consistency_score * 0.20
        + grounding_score * 0.30
        + sentiment_score * 0.35
        + confidence_score * 0.15
    )

    # --- Verdict ---
    if trust_score >= 70:
        verdict = "TRUST"
    elif trust_score >= 45:
        verdict = "REVIEW"
    else:
        verdict = "FLAG"

    # --- Reason: one specific sentence based on the weakest sub-score ---
    weakest_label = min(
        ("Consistency", consistency_score),
        ("Grounding", grounding_score),
        ("Sentiment Alignment", sentiment_score),
        ("Confidence", confidence_score),
        key=lambda x: x[1],
    )[0]
    weakest_score = {
        "Consistency": consistency_score,
        "Grounding": grounding_score,
        "Sentiment Alignment": sentiment_score,
        "Confidence": confidence_score,
    }[weakest_label]

    if weakest_label == "Consistency":
        reason = (
            f"Consistency is {weakest_score:.0f}/100 — the model gave meaningfully "
            f"different explanations across runs, suggesting it is improvising rather "
            f"than reasoning from the actual metrics."
        )
    elif weakest_label == "Grounding":
        reason = (
            f"Grounding is {weakest_score:.0f}/100 — the explanation did not reference "
            f"the real function name, file, or metric values, making it generic rather "
            f"than specific to this function."
        )
    elif weakest_label == "Sentiment Alignment":
        reason = (
            f"Sentiment alignment is {weakest_score:.0f}/100 — the explanation's tone "
            f"does not match the actual risk level of this function, suggesting the model "
            f"may be misrepresenting the severity."
        )
    else:  # Confidence
        reason = (
            f"Confidence is {weakest_score:.0f}/100 — the explanation contains hedging "
            f"language, suggesting the model is uncertain about its own claims."
        )

    return {
        "trust_score": round(trust_score, 1),
        "consistency_score": round(consistency_score, 1),
        "grounding_score": round(grounding_score, 1),
        "sentiment_score": round(sentiment_score, 1),
        "confidence_score": round(confidence_score, 1),
        "verdict": verdict,
        "reason": reason,
    }

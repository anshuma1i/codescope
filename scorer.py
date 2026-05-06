"""
Module for risk scoring.
Contains risk scoring logic based on code analysis metrics.
"""

from typing import List, Dict, Any


def calculate_risk_score(func_metrics: Dict[str, Any]) -> float:
    """Computes a risk score for a single function based on its metrics."""
    complexity = func_metrics.get('complexity', 0)
    nloc = func_metrics.get('nloc', 0)
    parameters = func_metrics.get('parameters', 0)
    token_count = func_metrics.get('token_count', 0)
    mi = func_metrics.get('maintainability_index')

    token_penalty = max(0, (token_count - 200)) * 0.1
    maintainability_penalty = max(0, (50 - mi)) * 1.5 if mi is not None else 0.0

    return float((complexity * 3.0) + (nloc * 0.5) + (parameters * 4.0) + token_penalty + maintainability_penalty)


def classify_risk(score: float) -> str:
    """Converts a risk score into a category string."""
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "moderate"
    return "low"


def score_and_rank(analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates risk scores for all results and sorts them descending by score."""
    for result in analysis_results:
        score = calculate_risk_score(result)
        result['risk_score'] = round(score, 1)
        result['risk_level'] = classify_risk(score)
    return sorted(analysis_results, key=lambda x: x.get('risk_score', 0), reverse=True)


def get_top_risks(scored_results: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    """Returns the top n riskiest functions."""
    return scored_results[:n]


def count_risk_levels(scored_results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Counts functions at each risk level."""
    counts = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    for r in scored_results:
        level = r.get('risk_level', 'low')
        counts[level] = counts.get(level, 0) + 1
    return counts


def find_riskiest_file(scored_results: List[Dict[str, Any]]) -> str:
    """Finds the file with the highest average risk score."""
    if not scored_results:
        return "N/A"
    file_scores: Dict[str, List[float]] = {}
    for r in scored_results:
        file_scores.setdefault(r.get('file', 'unknown'), []).append(r.get('risk_score', 0.0))
    return max(file_scores, key=lambda f: sum(file_scores[f]) / len(file_scores[f]))


def _compute_averages(scored_results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Computes average complexity and risk score."""
    n = max(1, len(scored_results))
    return {
        "average_complexity": round(sum(r.get('complexity', 0) for r in scored_results) / n, 1),
        "average_risk_score": round(sum(r.get('risk_score', 0.0) for r in scored_results) / n, 1),
    }


def _extract_languages(scored_results: List[Dict[str, Any]]) -> List[str]:
    """Extracts unique languages from results."""
    return list({r['language'] for r in scored_results if 'language' in r})


def get_summary_stats(scored_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates overall summary statistics across all analyzed and scored functions."""
    risk_counts = count_risk_levels(scored_results)
    averages = _compute_averages(scored_results)
    return {
        "total_functions": len(scored_results),
        "critical_count": risk_counts["critical"],
        "high_count": risk_counts["high"],
        "moderate_count": risk_counts["moderate"],
        "low_count": risk_counts["low"],
        "average_complexity": averages["average_complexity"],
        "average_risk_score": averages["average_risk_score"],
        "riskiest_file": find_riskiest_file(scored_results),
        "languages_analyzed": _extract_languages(scored_results),
    }


if __name__ == "__main__":
    import sys
    from analyzer import analyze_directory, enrich_with_radon
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    results = analyze_directory(directory)
    results = enrich_with_radon(results, directory)
    scored = score_and_rank(results)

    print("\n=== TOP 10 RISKIEST FUNCTIONS ===")
    for r in get_top_risks(scored):
        print(f"[{r['risk_level'].upper()}] {r['file']}::{r['function']} | risk={r['risk_score']} | complexity={r['complexity']} | nloc={r['nloc']}")

    print("\n=== SUMMARY ===")
    stats = get_summary_stats(scored)
    for k, v in stats.items():
        print(f"  {k}: {v}")

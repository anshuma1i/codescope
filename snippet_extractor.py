"""
Module for snippet extraction.
Will extract code snippets from source files for analysis.
"""

import os
import sys
from typing import List, Dict, Any

def extract_snippet(file_path: str, start_line: int, end_line: int, context_lines: int = 3) -> str:
    """
    Reads the source file and extracts lines adding line numbers with context lines around it.
    """
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    start_idx = max(1, start_line - context_lines) - 1
    end_idx = end_line + context_lines
    
    snippet_lines = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= start_idx and i < end_idx:
                    snippet_lines.append(f"{i + 1:4} | {line.rstrip(chr(10))}")
                elif i >= end_idx:
                    break
        return "\n".join(snippet_lines)
    except Exception as e:
        return f"Error reading file {file_path}: {e}"

def build_llm_context(top_risks: List[Dict[str, Any]], base_directory: str, max_functions: int = 5, max_snippet_lines: int = 100) -> str:
    """
    Builds a structured text block of risk context and actual source code for LLM consumption.
    """
    blocks = []
    
    functions_to_process = top_risks[:max_functions]
    
    for i, func in enumerate(functions_to_process, 1):
        rel_path = func.get("file", "unknown")
        full_path = os.path.join(base_directory, rel_path)
        function_name = func.get("function", "unknown")
        start_line = func.get("start_line", 0)
        end_line = func.get("end_line", 0)
        
        snippet = extract_snippet(full_path, start_line, end_line)
        
        snippet_split = snippet.split("\n")
        if len(snippet_split) > max_snippet_lines:
            snippet = "\n".join(snippet_split[:max_snippet_lines])
            snippet += f"\n... (truncated, showing first {max_snippet_lines} lines)"
            
        maintainability = func.get("maintainability_index")
        maintainability_str = f"{maintainability:.1f}" if maintainability is not None else "N/A"
        grade = func.get('complexity_grade', 'N/A')
        
        block = f"""--- FUNCTION {i} of {len(functions_to_process)} ---
File: {rel_path}
Function: {function_name}
Lines: {start_line}-{end_line}
Language: {func.get('language', 'unknown')}
Metrics:
  Cyclomatic Complexity: {func.get('complexity', 0)} (Grade: {grade})
  Lines of Code: {func.get('nloc', 0)}
  Parameters: {func.get('parameters', 0)}
  Risk Score: {func.get('risk_score', 0.0)} ({str(func.get('risk_level', 'unknown')).upper()})
  Maintainability Index: {maintainability_str}

Source Code:
```
{snippet}
```
---"""
        blocks.append(block)
        
    return "\n\n".join(blocks)

def build_summary_context(summary_stats: Dict[str, Any]) -> str:
    """
    Formats the codebase summary statistics as a readable text block.
    """
    langs = summary_stats.get("languages_analyzed", [])
    langs_str = ", ".join(langs) if langs else "none"
    
    block = f"""=== CODEBASE OVERVIEW ===
Total Functions Analyzed: {summary_stats.get("total_functions", 0)}
Languages: {langs_str}
Average Complexity: {summary_stats.get("average_complexity", 0.0)}
Average Risk Score: {summary_stats.get("average_risk_score", 0.0)}

Risk Distribution:
  Critical: {summary_stats.get("critical_count", 0)} functions
  High: {summary_stats.get("high_count", 0)} functions
  Moderate: {summary_stats.get("moderate_count", 0)} functions
  Low: {summary_stats.get("low_count", 0)} functions

Riskiest File: {summary_stats.get("riskiest_file", "none")}"""
    return block

if __name__ == "__main__":
    from analyzer import analyze_directory, enrich_with_radon
    from scorer import score_and_rank, get_top_risks, get_summary_stats
    
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    
    results = analyze_directory(directory)
    results = enrich_with_radon(results, directory)
    scored = score_and_rank(results)
    
    top = get_top_risks(scored, n=3)
    stats = get_summary_stats(scored)
    
    print(build_summary_context(stats))
    print()
    print(build_llm_context(top, directory, max_functions=3))

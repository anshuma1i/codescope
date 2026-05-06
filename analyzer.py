"""
Module for code analysis.
Contains code analysis functions using lizard and radon.
"""

import os
import sys
import concurrent.futures
from typing import List, Dict, Any, Set

try:
    import lizard
    from radon.complexity import cc_visit, cc_rank
    from radon.metrics import mi_visit
except ImportError:
    pass

# Directories to skip during analysis
EXCLUDED_DIRS: Set[str] = {
    '__pycache__', 'venv', 'env', '.env', 'node_modules', '.git',
    'build', 'dist', '.tox', '.eggs', '.mypy_cache', '.pytest_cache',
    'coverage', 'target', 'site-packages', 'test', 'tests',
    'testing', 'test_data', 'testdata'
}

VALID_EXTENSIONS: Set[str] = {'.py', '.java'}


def should_skip_directory(dir_name: str) -> bool:
    """Returns True if directory should be skipped during analysis."""
    return dir_name.startswith('.') or dir_name.lower() in EXCLUDED_DIRS


def should_skip_file(file_name: str) -> bool:
    """Returns True if file should be skipped during analysis."""
    _, ext = os.path.splitext(file_name)
    return file_name.startswith('.') or ext not in VALID_EXTENSIONS or 'test' in file_name.lower()


def collect_file_paths(directory_path: str) -> List[str]:
    """Walks directory tree and returns list of valid file paths to analyze."""
    file_paths = []
    for root, dirs, files in os.walk(directory_path):
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]
        for f in files:
            if not should_skip_file(f):
                file_paths.append(os.path.join(root, f))
    return file_paths


def run_parallel_analysis(file_paths: List[str], directory_path: str) -> List[Dict[str, Any]]:
    """Runs analyze_file in parallel across all file paths and collects results."""
    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        future_to_path = {executor.submit(analyze_file, path): path for path in file_paths}
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                file_results = future.result()
                for r in file_results:
                    r["file"] = os.path.relpath(path, directory_path)
                results.extend(file_results)
            except Exception as e:
                print(f"Error analyzing {path}: {e}", file=sys.stderr)
    return results


def analyze_directory(directory_path: str) -> List[Dict[str, Any]]:
    """Walks through all .py and .java files in the given directory (recursively),
    skips hidden folders, caches, and test files. Returns a combined list of metrics."""
    file_paths = collect_file_paths(directory_path)
    return run_parallel_analysis(file_paths, directory_path)


def analyze_file(file_path: str) -> List[Dict[str, Any]]:
    """Uses lizard to analyze a file and returns a list of dicts, one per function."""
    results: List[Dict[str, Any]] = []
    try:
        analysis = lizard.analyze_file(file_path)
        language = "python" if file_path.endswith('.py') else "java"
        for func in analysis.function_list:
            results.append({
                "file": file_path,
                "function": func.name,
                "long_name": func.long_name,
                "start_line": func.start_line,
                "end_line": func.end_line,
                "nloc": func.nloc,
                "complexity": func.cyclomatic_complexity,
                "token_count": func.token_count,
                "parameters": func.parameter_count,
                "language": language
            })
    except Exception as e:
        print(f"Error in lizard analysis for {file_path}: {e}", file=sys.stderr)
    return results


def get_file_metrics(file_path: str) -> Dict[str, Any]:
    """Gets Python file metrics using radon (maintainability index and complexity grades)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        mi = mi_visit(code, multi=True)
        grades = {block.name: cc_rank(block.complexity) for block in cc_visit(code)}
        return {"maintainability_index": mi, "radon_grades": grades}
    except Exception as e:
        print(f"Error in radon analysis for {file_path}: {e}", file=sys.stderr)
        return {"maintainability_index": 0.0, "radon_grades": {}}


def apply_radon_metrics(func_result: Dict[str, Any], cache: Dict[str, Dict[str, Any]], base_dir: str) -> Dict[str, Any]:
    """Applies radon metrics to a single function result."""
    defaults = {"maintainability_index": None, "complexity_grade": None}
    func_result.update(defaults)
    if func_result.get("language") != "python":
        return func_result
    full_path = os.path.join(base_dir, func_result["file"])
    file_m = cache.get(full_path, {"maintainability_index": 0.0, "radon_grades": {}})
    func_result["maintainability_index"] = file_m.get("maintainability_index", 0.0)
    func_result["complexity_grade"] = file_m.get("radon_grades", {}).get(func_result.get("function"), "N/A")
    return func_result


def build_radon_cache(python_files: List[str]) -> Dict[str, Dict[str, Any]]:
    """Builds a cache of radon metrics for all Python files using parallel execution."""
    cache: Dict[str, Dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        future_to_path = {executor.submit(get_file_metrics, p): p for p in python_files}
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                cache[path] = future.result()
            except Exception as e:
                print(f"Error caching radon for {path}: {e}", file=sys.stderr)
                cache[path] = {"maintainability_index": 0.0, "radon_grades": {}}
    return cache


def enrich_with_radon(analysis_results: List[Dict[str, Any]], base_directory: str) -> List[Dict[str, Any]]:
    """Adds radon data to Python function results."""
    python_files = list({os.path.join(base_directory, r["file"]) for r in analysis_results if r.get("language") == "python"})
    cache = build_radon_cache(python_files)
    return [apply_radon_metrics(r, cache, base_directory) for r in analysis_results]


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    res = analyze_directory(directory)
    res = enrich_with_radon(res, directory)
    for r in res:
        print(f"{r['file']}::{r['function']} | complexity={r['complexity']} | nloc={r['nloc']} | params={r['parameters']} | grade={r.get('complexity_grade', 'N/A')}")

"""
Module for report generation.
Will call Gemini API to generate reports based on code analysis and risk scores.
"""

import os
import sys
from typing import Tuple, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

def setup_client(system_instruction: str = None) -> genai.GenerativeModel:
    """Loads GEMINI_API_KEY from .env, configures API, and returns the model."""
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your-key-here":
        raise ValueError("GEMINI_API_KEY is missing or incorrectly set in .env file. Please provide a valid key.")
    
    genai.configure(api_key=api_key)
    
    if system_instruction:
        return genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
    return genai.GenerativeModel("gemini-2.5-flash")

def build_grounded_prompt(summary_context: str, llm_context: str) -> Tuple[str, str]:
    """Returns the system and user prompts with grounded strict rules."""
    system_prompt = """You are a senior software quality consultant who writes reports for CTOs and engineering managers. Your job is to translate technical code quality findings into clear business language.

STRICT RULES:
- Every claim you make MUST reference a specific file path, function name, and line number from the data provided
- If you cannot back a claim with evidence from the provided data, do NOT make it
- Do NOT invent or hallucinate any code, file names, or metrics not present in the data
- Focus on business impact: maintenance cost, bug risk, onboarding difficulty, deployment risk
- Be specific and actionable, not generic

REPORT STRUCTURE:
1. Executive Summary (3-4 sentences: overall health verdict, biggest concern, recommended action)
2. Top 3 Critical Risks (for each: what the problem is in plain English, which file/function/line, why it matters to the business, specific fix recommendation)
3. Codebase Health Overview (interpret the risk distribution numbers in business terms)
4. Recommended Action Plan (prioritized list of what to fix first and why, estimated effort as low/medium/high)"""

    user_prompt = f"""Analyze the following codebase and generate a quality report.

{summary_context}

{llm_context}

Generate the report now. Remember: every claim must reference specific files, functions, and line numbers from the data above."""

    return system_prompt, user_prompt

def generate_report(summary_context: str, llm_context: str) -> str:
    """Generates the grounded report using the Gemini API."""
    try:
        system_prompt, user_prompt = build_grounded_prompt(summary_context, llm_context)
        model = setup_client(system_instruction=system_prompt)
        response = model.generate_content(user_prompt)
        return response.text
    except Exception as e:
        return f"Error generating report: {str(e)}"

def generate_report_comparison(summary_context: str, llm_context: str) -> Dict[str, str]:
    """Generates TWO reports with different prompting strategies to show prompt engineering awareness."""
    results = {}
    
    try:
        # Strategy A ("grounded")
        system_a, user_a = build_grounded_prompt(summary_context, llm_context)
        model_a = setup_client(system_instruction=system_a)
        response_a = model_a.generate_content(user_a)
        results["grounded"] = response_a.text
    except Exception as e:
        results["grounded"] = f"Error (Grounded): {str(e)}"
        
    try:
        # Strategy B ("basic")
        system_b = "You are a code quality expert. Analyze code and write reports."
        user_b = f"Write a code quality report for this codebase:\n\n{summary_context}\n\n{llm_context}"
        model_b = setup_client(system_instruction=system_b)
        response_b = model_b.generate_content(user_b)
        results["basic"] = response_b.text
    except Exception as e:
        results["basic"] = f"Error (Basic): {str(e)}"
        
    return results

if __name__ == "__main__":
    from analyzer import analyze_directory, enrich_with_radon
    from scorer import score_and_rank, get_top_risks, get_summary_stats
    from snippet_extractor import build_llm_context, build_summary_context
    
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    results = analyze_directory(directory)
    results = enrich_with_radon(results, directory)
    scored = score_and_rank(results)
    top = get_top_risks(scored, n=5)
    stats = get_summary_stats(scored)
    
    summary_ctx = build_summary_context(stats)
    llm_ctx = build_llm_context(top, directory, max_functions=5)
    
    print("Generating grounded report...")
    report = generate_report(summary_ctx, llm_ctx)
    print(report)

"""
Streamlit UI module.
Main entry point for the CodeScope interactive web application.
"""

import os
import html
import pandas as pd
import streamlit as st
import altair as alt

from analyzer import analyze_directory, enrich_with_radon
from scorer import score_and_rank, get_top_risks, get_summary_stats
from snippet_extractor import build_llm_context, build_summary_context
from report_generator import generate_report, setup_client, explain_finding
from repo_handler import is_github_url, clone_repo, cleanup_repo
from polygraph import score_explanation

st.set_page_config(
    page_title="CodeScope",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    :root {
        --cs-bg: #070B14;
        --cs-panel: #0A0F1C;
        --cs-panel-2: #0D1424;
        --cs-sidebar: #050811;
        --cs-line: #1E293B;
        --cs-line-soft: rgba(148, 163, 184, 0.14);
        --cs-text: #E2E8F0;
        --cs-muted: #94A3B8;
        --cs-dim: #64748B;
        --cs-accent: #FF4B4B;
        --cs-accent-2: #FF8C00;
        --cs-cyan: #38BDF8;
        --cs-critical: #FF0000;
        --cs-high: #FF8C00;
        --cs-moderate: #FFFF00;
        --cs-low: #008000;
    }

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background:
            linear-gradient(90deg, rgba(51, 65, 85, 0.13) 1px, transparent 1px),
            linear-gradient(0deg, rgba(51, 65, 85, 0.11) 1px, transparent 1px),
            linear-gradient(180deg, #070B14 0%, #0A0F1C 54%, #050811 100%) !important;
        background-size: 48px 48px, 48px 48px, auto !important;
        color: var(--cs-text) !important;
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(180deg, rgba(255, 75, 75, 0.08), transparent 24%),
            repeating-linear-gradient(180deg, rgba(255,255,255,0.025) 0, rgba(255,255,255,0.025) 1px, transparent 1px, transparent 7px);
        opacity: 0.7;
        z-index: 0;
    }

    .block-container {
        max-width: 1220px;
        padding-top: 3.2rem;
        padding-bottom: 4rem;
        position: relative;
        z-index: 1;
    }

    h1, h2, h3, h4, p, label, span, div {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .cs-hero {
        position: relative;
        padding: 1.25rem 0 2.1rem;
        text-align: center;
        border-bottom: 1px solid rgba(148, 163, 184, 0.13);
        margin-bottom: 1.5rem;
    }

    .cs-hero::after {
        content: "";
        position: absolute;
        left: 50%;
        bottom: -1px;
        width: min(560px, 74vw);
        height: 1px;
        transform: translateX(-50%);
        background: linear-gradient(90deg, transparent, rgba(255, 75, 75, 0.9), rgba(56, 189, 248, 0.72), transparent);
    }

    .cs-hero-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        color: var(--cs-muted);
        border: 1px solid rgba(148, 163, 184, 0.2);
        background: rgba(10, 15, 28, 0.72);
        padding: 0.42rem 0.68rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
        box-shadow: 0 0 22px rgba(56, 189, 248, 0.08);
    }

    .cs-hero-kicker span {
        width: 0.48rem;
        height: 0.48rem;
        border-radius: 999px;
        background: var(--cs-low);
        box-shadow: 0 0 12px rgba(0, 128, 0, 0.8);
    }

    .cs-hero h1 {
        margin: 0.85rem 0 0;
        color: var(--cs-accent);
        font-size: 5.2rem;
        font-weight: 900;
        letter-spacing: 0;
        line-height: 0.95;
        text-shadow: 0 0 34px rgba(255, 75, 75, 0.24);
    }

    .cs-hero h1 a {
        color: inherit !important;
        text-decoration: none !important;
        position: relative;
        transition: all 0.3s ease;
    }

    .cs-hero h1 a::after {
        content: "🔗";
        font-size: 2.2rem;
        position: absolute;
        right: -3.5rem;
        top: 50%;
        transform: translateY(-50%);
        opacity: 0;
        transition: all 0.3s ease;
        filter: drop-shadow(0 0 8px var(--cs-accent));
    }

    .cs-hero h1 a:hover {
        text-shadow: 0 0 45px rgba(255, 75, 75, 0.45);
    }

    .cs-hero h1 a:hover::after {
        opacity: 1;
        right: -2.8rem;
    }

    .cs-hero p {
        margin: 0.85rem 0 0;
        color: var(--cs-text);
        font-size: 1.35rem;
        font-weight: 500;
    }

    .cs-hero-strip {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin-top: 1.2rem;
    }

    .cs-hero-strip span {
        color: var(--cs-dim);
        background: rgba(13, 20, 36, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.13);
        border-radius: 999px;
        padding: 0.38rem 0.68rem;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0;
    }
    
    /* FUTURISTIC TABS STYLING */[data-testid="stTabs"] [data-baseweb="tablist"] {
        gap: 0.55rem;
        width: 100%;
        justify-content: space-between;
        background: rgba(10, 15, 28, 0.82);
        padding: 0.42rem;
        border-radius: 8px;
        border: 1px solid var(--cs-line);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 18px 50px rgba(0,0,0,0.24);
        margin-bottom: 1.5rem;
    }

    [data-testid="stTabs"] button[data-baseweb="tab"] {
        flex: 1;
        display: flex;
        justify-content: center;
        min-height: 3rem;
        font-size: 0.98rem !important;
        font-weight: 800 !important;
        letter-spacing: 0 !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
        color: var(--cs-dim) !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        padding: 0.78rem 0.95rem !important;
        transition: all 0.3s ease-in-out !important;
    }

    [data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        color: var(--cs-text) !important;
        background: rgba(255, 255, 255, 0.045) !important;
    }

    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--cs-accent) !important;
        background: rgba(255, 75, 75, 0.1) !important;
        border: 1px solid rgba(255, 75, 75, 0.5) !important;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.2) !important;
    }[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        display: none;
    }
    
    /* HIDE DEFAULT 'Press Enter to apply' in text input */
    div[data-testid="InputInstructions"] {
        display: none !important;
    }
    
    /* SIDEBAR & BUTTON FUTURISTIC STYLING */
    [data-testid="stSidebar"] {
        background-color: var(--cs-sidebar) !important;
        visibility: visible !important;
        z-index: 999 !important;
        border-right: 1px solid rgba(148, 163, 184, 0.14) !important;
    }
    [data-testid="stSidebarContent"] {
        background:
            linear-gradient(180deg, rgba(255, 75, 75, 0.08), transparent 25%),
            var(--cs-sidebar) !important;
        padding: 1.3rem 1rem !important;
    }
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapseButton"] {
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        color: var(--cs-text) !important;
        background: rgba(5, 8, 17, 0.72) !important;
        border: 1px solid var(--cs-line) !important;
        border-radius: 8px !important;
        z-index: 1000 !important;
    }

    .cs-side-brand {
        border: 1px solid rgba(148, 163, 184, 0.15);
        background: rgba(10, 15, 28, 0.78);
        border-radius: 8px;
        padding: 1rem;
        margin: 0.2rem 0 1rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 18px 36px rgba(0,0,0,0.24);
    }

    .cs-side-mark {
        color: var(--cs-accent);
        font-size: 1.4rem;
        font-weight: 900;
        line-height: 1;
        letter-spacing: 0;
    }

    .cs-side-subtitle {
        color: var(--cs-muted);
        font-size: 0.8rem;
        margin-top: 0.45rem;
        line-height: 1.4;
    }

    .cs-side-status {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.45rem;
        margin-top: 0.85rem;
    }

    .cs-side-status span {
        border: 1px solid rgba(148, 163, 184, 0.14);
        background: rgba(5, 8, 17, 0.6);
        border-radius: 8px;
        color: var(--cs-dim);
        font-size: 0.72rem;
        font-weight: 800;
        padding: 0.42rem 0.5rem;
        text-align: center;
    }[data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,[data-testid="stSidebar"] p {
        color: var(--cs-muted) !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        background: rgba(10, 15, 28, 0.9) !important;
        border: 1px solid rgba(148, 163, 184, 0.22) !important;
        border-radius: 8px !important;
        color: var(--cs-text) !important;
        font-weight: 650 !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035) !important;
    }[data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: rgba(255, 75, 75, 0.72) !important;
        box-shadow: 0 0 0 1px rgba(255, 75, 75, 0.18), 0 0 28px rgba(255, 75, 75, 0.12) !important;
    }

    [data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(90deg, #FF4B4B, #FF8C00) !important;
        border: none !important;
        color: white !important;
        font-weight: 800 !important;
        letter-spacing: 0 !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3) !important;
        transition: all 0.3s ease-in-out !important;
        border-radius: 8px !important;
        min-height: 2.9rem !important;
    }
    [data-testid="stSidebar"] button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(255, 75, 75, 0.6) !important;
    }

    /* CUSTOM METRICS CARDS */
    div[data-testid="metric-container"] {
        background: linear-gradient(180deg, rgba(13, 20, 36, 0.95), rgba(8, 12, 22, 0.95));
        border: 1px solid var(--cs-line);
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 18px 42px rgba(0,0,0,0.2);
    }
    div[data-testid="metric-container"] label {
        color: var(--cs-dim) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0 !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: var(--cs-text) !important;
        font-family: monospace !important;
        font-weight: 800 !important;
        font-variant-numeric: tabular-nums !important;
    }

    .cs-section-title {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        color: var(--cs-text);
        font-weight: 900;
        letter-spacing: 0;
        border-bottom: 1px solid var(--cs-line);
        padding-bottom: 0.72rem;
        margin: 1.6rem 0 1.15rem;
        text-transform: uppercase;
    }

    .cs-section-title::before {
        content: "";
        width: 2.4rem;
        height: 2px;
        background: linear-gradient(90deg, var(--cs-accent), var(--cs-cyan));
        border-radius: 999px;
    }

    .cs-telemetry {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1rem;
        background: rgba(10, 15, 28, 0.86);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--cs-line);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 20px 52px rgba(0,0,0,0.22);
    }

    .cs-tile {
        min-height: 8.5rem;
        border: 1px solid rgba(148, 163, 184, 0.13);
        background:
            linear-gradient(180deg, rgba(13, 20, 36, 0.95), rgba(5, 8, 17, 0.76));
        border-radius: 8px;
        padding: 1.05rem;
        text-align: center;
    }

    .cs-tile-value {
        font-size: 2.45rem;
        font-weight: 900;
        font-variant-numeric: tabular-nums;
        line-height: 1;
    }

    .cs-tile-value span {
        font-size: 1.05rem;
        opacity: 0.72;
    }

    .cs-tile-label {
        color: var(--cs-muted);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0;
        margin-top: 0.78rem;
        font-weight: 800;
    }

    .cs-tile-count {
        color: var(--cs-dim);
        margin-top: 0.24rem;
        font-size: 0.98rem;
        font-weight: 700;
    }

    .cs-empty {
        border: 1px solid rgba(148, 163, 184, 0.14);
        background:
            linear-gradient(135deg, rgba(255, 75, 75, 0.08), transparent 28%),
            linear-gradient(180deg, rgba(10, 15, 28, 0.9), rgba(5, 8, 17, 0.86));
        border-radius: 8px;
        padding: 1.35rem;
        margin-top: 1.2rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 24px 70px rgba(0,0,0,0.28);
    }

    .cs-empty-header {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: center;
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
        padding-bottom: 0.9rem;
        margin-bottom: 1rem;
    }

    .cs-empty-title {
        color: var(--cs-text);
        font-size: 1.05rem;
        font-weight: 900;
        text-transform: uppercase;
    }

    .cs-empty-status {
        color: var(--cs-low);
        border: 1px solid rgba(0, 128, 0, 0.35);
        background: rgba(0, 128, 0, 0.08);
        border-radius: 999px;
        padding: 0.34rem 0.6rem;
        font-size: 0.74rem;
        font-weight: 900;
    }

    .cs-empty-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
    }

    .cs-empty-cell {
        min-height: 5.6rem;
        border-radius: 8px;
        border: 1px solid rgba(148, 163, 184, 0.12);
        background: rgba(13, 20, 36, 0.62);
        padding: 0.8rem;
    }

    .cs-empty-cell strong {
        color: var(--cs-text);
        display: block;
        font-size: 0.9rem;
        margin-bottom: 0.36rem;
    }

    .cs-empty-cell span {
        color: var(--cs-dim);
        font-size: 0.78rem;
        line-height: 1.35;
    }

    .cs-file-pill {
        border: 1px solid rgba(148, 163, 184, 0.15);
        background: rgba(10, 15, 28, 0.76);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        color: var(--cs-text);
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.92rem;
        overflow-wrap: anywhere;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.035);
    }[data-testid="stDataFrame"],
    [data-testid="stJson"],[data-testid="stExpander"] {
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid rgba(148, 163, 184, 0.16) !important;
        background: rgba(10, 15, 28, 0.74) !important;
    }

    [data-testid="stDownloadButton"] button,[data-testid="stButton"] button {
        border-radius: 8px !important;
        font-weight: 800 !important;
        letter-spacing: 0 !important;
        border: 1px solid rgba(148, 163, 184, 0.18) !important;
        background: rgba(13, 20, 36, 0.92) !important;
        color: var(--cs-text) !important;
    }[data-testid="stDownloadButton"] button:hover,
    [data-testid="stButton"] button:hover {
        border-color: rgba(255, 75, 75, 0.55) !important;
        color: white !important;
        box-shadow: 0 0 24px rgba(255, 75, 75, 0.16) !important;
    }

    /* CLEAN HEADER BUT KEEP BUTTONS ACCESSIBLE */
    header[data-testid="stHeader"] { 
        background-color: rgba(0,0,0,0) !important;
        visibility: visible !important;
    }
    div[data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
        background: transparent !important;
    }
    [data-testid="stToolbarActions"],[data-testid="stStatusWidget"],
    [data-testid="stMainMenu"],
    [data-testid="stAppDeployButton"] {
        display: none !important;
    }
    footer { display: none !important; }

    /* CUSTOM SCROLLBARS */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: var(--cs-panel); }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--cs-accent); }

    @media (max-width: 900px) {
        .block-container {
            padding-top: 2.35rem;
        }
        .cs-hero h1 {
            font-size: 4rem;
        }
        .cs-telemetry,
        .cs-empty-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 640px) {
        .cs-hero h1 {
            font-size: 3.2rem;
        }
        .cs-hero p {
            font-size: 1rem;
        }
        .cs-telemetry,
        .cs-empty-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
<div class="cs-hero">
    <div class="cs-hero-kicker"><span></span> Static Analysis Control Deck</div>
    <h1><a href="https://github.com/anshuma1i/codescope" target="_blank">CodeScope</a></h1>
    <p>An AI-powered code quality analyzer</p>
    <div class="cs-hero-strip">
        <span>Lizard</span>
        <span>Radon</span>
        <span>Gemini</span>
        <span>Python</span>
        <span>Java</span>
    </div>
</div>
""", unsafe_allow_html=True)

@st.cache_data
def run_analysis(directory: str):
    results = analyze_directory(directory)
    results = enrich_with_radon(results, directory)
    scored = score_and_rank(results)
    stats = get_summary_stats(scored)
    return scored, stats

with st.sidebar:
    st.markdown("""
    <div class="cs-side-brand">
        <div class="cs-side-mark">CodeScope</div>
        <div class="cs-side-subtitle">Static metrics, ranked risk, grounded AI reports.</div>
        <div class="cs-side-status">
            <span>Python</span>
            <span>Java</span>
            <span>Lizard</span>
            <span>Radon</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    directory_input = st.text_input("Local path or GitHub URL", value="", placeholder="e.g. /tmp/test-requests or https://github.com/user/repo")
    st.markdown("<div style='font-size: 0.8rem; color: #64748B; margin-top: -10px; margin-bottom: 15px;'>Press Enter to lock in path</div>", unsafe_allow_html=True)
    top_n = int(st.number_input("Top N risky functions to analyze", value=5, min_value=1, max_value=20))
    st.divider()
    analyze_btn = st.button("Analyze", type="primary")
    st.markdown("---")
    st.markdown("**Run profile:** local files only")
    st.markdown("*No source code is uploaded during static analysis.*")

if analyze_btn:
    if not directory_input.strip():
        st.warning("Please enter a directory path or GitHub URL")
    else:
        input_normalized = directory_input.strip()
        temp_dir = None
        repo_url = None
        
        try:
            if is_github_url(input_normalized):
                with st.spinner("Cloning repository..."):
                    temp_dir, repo_url = clone_repo(input_normalized)
                analysis_path = temp_dir
                st.session_state['is_remote'] = True
                st.session_state['remote_url'] = repo_url
            else:
                if not os.path.exists(input_normalized):
                    st.error(f"Directory '{input_normalized}' not found")
                    st.stop()
                analysis_path = input_normalized
                st.session_state['is_remote'] = False
            
            st.session_state['analysis_done'] = True
            st.session_state['run_dir'] = analysis_path
            st.session_state['run_top_n'] = top_n
            st.session_state['temp_dir'] = temp_dir
            for k in['grounded_report', 'basic_report', 'show_basic']:
                st.session_state.pop(k, None)
        except RuntimeError as e:
            st.error(f"Failed to clone repository: {e}")
            if temp_dir:
                cleanup_repo(temp_dir)
            st.stop()

if not st.session_state.get('analysis_done', False):
    st.markdown("""
    <div class="cs-empty">
        <div class="cs-empty-header">
            <div class="cs-empty-title">Awaiting Repository Signal</div>
            <div class="cs-empty-status">READY</div>
        </div>
        <div class="cs-empty-grid">
            <div class="cs-empty-cell">
                <strong>Scan Core</strong>
                <span>Parallel file discovery with deterministic complexity metrics.</span>
            </div>
            <div class="cs-empty-cell">
                <strong>Risk Engine</strong>
                <span>Severity mapping locked to Critical, High, Moderate, and Low.</span>
            </div>
            <div class="cs-empty-cell">
                <strong>Report Layer</strong>
                <span>Grounded markdown summaries based on exact static analysis data.</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.get('analysis_done', False):
    run_dir = st.session_state['run_dir']
    run_n = st.session_state['run_top_n']
    temp_dir = st.session_state.get('temp_dir')
    is_remote = st.session_state.get('is_remote', False)
    remote_url = st.session_state.get('remote_url', '')

    # Run analysis (cached - only executes once per directory)
    scored_results, summary_stats = run_analysis(run_dir)

    # Clean up temp dir after analysis is cached
    if temp_dir:
        cleanup_repo(temp_dir)
        st.session_state['temp_dir'] = None

    if is_remote and remote_url:
        st.caption(f"Repository: {remote_url}")

    if not scored_results or summary_stats.get("total_functions", 0) == 0:
        st.warning("No Python or Java files found in this directory")
    else:
        top_risks = get_top_risks(scored_results, n=run_n)

        # Pre-compute LLM context (needed by both tab2 and tab3)
        summary_ctx = build_summary_context(summary_stats)
        llm_ctx = build_llm_context(top_risks, run_dir, max_functions=run_n)

        # Extract stats for dashboard
        crit = summary_stats.get("critical_count", 0)
        high = summary_stats.get("high_count", 0)
        mod = summary_stats.get("moderate_count", 0)
        low = summary_stats.get("low_count", 0)
        total = summary_stats.get("total_functions", 1) or 1

        tab1, tab2, tab3, tab4 = st.tabs(["Metrics Dashboard", "AI Report", "Prompt Comparison", "Per-Function Explanations"])

        # ==================== TAB 1: METRICS DASHBOARD ====================
        with tab1:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Functions", summary_stats.get("total_functions", 0))
            col2.metric("Critical Count", summary_stats.get("critical_count", 0))
            col3.metric("Average Complexity", summary_stats.get("average_complexity", 0.0))
            col4.metric("Average Risk Score", summary_stats.get("average_risk_score", 0.0))

            st.divider()
            st.markdown('<div class="cs-section-title">Codebase Health Telemetry</div>', unsafe_allow_html=True)

            st.markdown(f"""
            <div class="cs-telemetry">
                <div class="cs-tile">
                    <div class="cs-tile-value" style="color: #FF0000; text-shadow: 0 0 15px rgba(255,0,0,0.3);">{crit/total*100:.1f}<span>%</span></div>
                    <div class="cs-tile-label">Critical Load</div>
                    <div class="cs-tile-count">{crit} funcs</div>
                </div>
                <div class="cs-tile">
                    <div class="cs-tile-value" style="color: #FF8C00; text-shadow: 0 0 15px rgba(255,140,0,0.3);">{high/total*100:.1f}<span>%</span></div>
                    <div class="cs-tile-label">High Warning</div>
                    <div class="cs-tile-count">{high} funcs</div>
                </div>
                <div class="cs-tile">
                    <div class="cs-tile-value" style="color: #FFFF00; text-shadow: 0 0 15px rgba(255,255,0,0.3);">{mod/total*100:.1f}<span>%</span></div>
                    <div class="cs-tile-label">Mod Activity</div>
                    <div class="cs-tile-count">{mod} funcs</div>
                </div>
                <div class="cs-tile">
                    <div class="cs-tile-value" style="color: #008000; text-shadow: 0 0 15px rgba(0,128,0,0.3);">{low/total*100:.1f}<span>%</span></div>
                    <div class="cs-tile-label">Optimal State</div>
                    <div class="cs-tile-count">{low} funcs</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            risk_counts = {
                "Risk Level":["Critical", "High", "Moderate", "Low"],
                "Count": [crit, high, mod, low]
            }
            df_dist = pd.DataFrame(risk_counts)

            chart = alt.Chart(df_dist).mark_bar(
                color='#334155',
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
                size=50
            ).encode(
                x=alt.X('Risk Level', sort=None, axis=alt.Axis(labelAngle=0, title='', labelColor='#94A3B8', labelFontSize=13, grid=False)),
                y=alt.Y('Count', axis=alt.Axis(labelAngle=0, title='COUNT', titleAngle=0, titleAlign='left', titleY=-20, titleX=-10, labelColor='#94A3B8', titleColor='#64748B', tickCount=4, grid=False))
            ).properties(height=250, background='transparent')

            chart = chart.configure_view(
                strokeWidth=0
            ).configure_axis(
                grid=False,
                domainColor='#1E293B',
                tickColor='#1E293B'
            )

            st.altair_chart(chart, use_container_width=True)

            st.markdown('<div class="cs-section-title">Top Risky Functions</div>', unsafe_allow_html=True)
            cols_to_show =["file", "function", "complexity", "nloc", "parameters", "risk_score", "risk_level", "complexity_grade"]
            available_cols =[c for c in cols_to_show if c in top_risks[0]] if top_risks else[]
            df_risks = pd.DataFrame(top_risks)[available_cols] if top_risks else pd.DataFrame()

            risk_emoji = {"critical": "🔴 critical", "high": "🟠 high", "moderate": "🟡 moderate", "low": "🟢 low"}

            if not df_risks.empty:
                if 'risk_score' in df_risks.columns:
                    df_risks['risk_score'] = df_risks['risk_score'].apply(lambda x: f"{float(x):.1f}")
                if 'risk_level' in df_risks.columns:
                    df_risks['risk_level'] = df_risks['risk_level'].apply(lambda x: risk_emoji.get(x, x))
                st.dataframe(df_risks, use_container_width=True)
            else:
                st.info("No risky functions found.")

            st.markdown('<div class="cs-section-title">Riskiest File</div>', unsafe_allow_html=True)
            riskiest_file = html.escape(str(summary_stats.get("riskiest_file", "None")))
            st.markdown(f'<div class="cs-file-pill">{riskiest_file}</div>', unsafe_allow_html=True)

        # ==================== TAB 2: AI REPORT ====================
        with tab2:
            with st.expander("How this report was generated"):
                st.markdown("This report was generated using Google Gemini with a carefully engineered prompt that enforces grounded explanations. The LLM is constrained to only reference specific files, functions, and line numbers from the static analysis data, so it cannot hallucinate or make unsupported claims. This approach ensures that LLMs use deterministic ground truth for reliable code quality insights.")

            if 'grounded_report' not in st.session_state:
                with st.spinner("Generating AI-powered quality report via Gemini..."):
                    st.session_state['grounded_report'] = generate_report(summary_ctx, llm_ctx)

            st.markdown(st.session_state.get('grounded_report', ''))
            st.download_button("Download Report", data=st.session_state.get('grounded_report', ''), file_name="CodeScope_Report.md", mime="text/markdown")

            with st.expander("View raw analysis data"):
                st.json(top_risks)

        # ==================== TAB 3: PROMPT COMPARISON ====================
        with tab3:
            # Show generate button only if no basic report yet
            if not st.session_state.get('basic_report') and not st.session_state.get('running_comparison'):
                st.info("Click 'Run Comparison' to generate a basic (ungrounded) report and compare it side-by-side with the grounded report.")
                if st.button("Run Comparison", key="run_comparison_btn"):
                    st.session_state['running_comparison'] = True
                    st.rerun()

            if st.session_state.get('running_comparison') and not st.session_state.get('basic_report'):
                with st.spinner("Generating basic report for comparison..."):
                    try:
                        sys_prompt = "You are a code quality expert. Analyze code and write reports. Do NOT include any dates in the report."
                        usr_prompt = f"Write a code quality report for this codebase:\n\n{summary_ctx}\n\n{llm_ctx}"
                        m = setup_client(system_instruction=sys_prompt)
                        resp = m.generate_content(usr_prompt)
                        st.session_state['basic_report'] = resp.text
                    except Exception as e:
                        st.session_state['basic_report'] = f"Error generating basic report: {e}"
                    st.session_state['running_comparison'] = False
                    st.rerun()

            # Show side-by-side comparison if basic report exists
            if st.session_state.get('basic_report'):
                col_left, col_right = st.columns(2)
                with col_left:
                    st.subheader("Grounded Prompt")
                    st.markdown(st.session_state.get('grounded_report', ''))
                with col_right:
                    st.subheader("Basic Prompt")
                    st.markdown(st.session_state.get('basic_report', ''))

        # ==================== TAB 4: PER-FUNCTION EXPLANATIONS ====================
        with tab4:
            st.markdown('<div class="cs-section-title">Per-Function AI Explanations</div>', unsafe_allow_html=True)
            demo_mode = st.toggle("Demo: contradiction test", value=False)
            if demo_mode:
                top_risks = [{
                    "file": "payment_service.py",
                    "function": "process_refund",
                    "complexity": 34,
                    "nloc": 89,
                    "risk_score": 91.0,
                    "risk_level": "critical",
                    "maintainability_index": 12.0,
                    "parameters": 7,
                    "start_line": 1,
                    "end_line": 89,
                    "language": "python"
                }]
            for idx, func in enumerate(top_risks):
                cache_key = f"explanation_stress_test" if demo_mode else f"explanation_{func['file']}_{func['function']}"
                poly_key = f"polygraph_stress_test" if demo_mode else f"polygraph_{func['file']}_{func['function']}"
                with st.expander(f"{func['function']} — {func['file']}  [{func['risk_level'].upper()}]"):
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    col_m1.metric("Complexity", func.get("complexity", "N/A"))
                    col_m2.metric("Lines of Code", func.get("nloc", "N/A"))
                    col_m3.metric("Risk Score", func.get("risk_score", "N/A"))
                    col_m4.metric("Parameters", func.get("parameters", "N/A"))

                    # Demo mode: pre-populate with fixed contradiction pair (no LLM call)
                    if demo_mode:
                        demo_explanation = (
                            "The process_refund function in payment_service.py is straightforward "
                            "and simple to understand. This is a clean, manageable function that is "
                            "unlikely to cause any issues. It is easy to maintain and new developers "
                            "should be able to work with it quickly without difficulty."
                        )
                        st.session_state[cache_key] = demo_explanation
                        st.session_state[poly_key] = score_explanation(func, demo_explanation)

                    if cache_key not in st.session_state:
                        if st.button("Explain this function", key=f"explain_btn_{idx}"):
                            with st.spinner("Generating explanation..."):
                                st.session_state[cache_key] = explain_finding(func)
                            st.rerun()
                    else:
                        st.markdown("---")
                        st.markdown(st.session_state[cache_key])

                        if demo_mode:
                            st.markdown(
                                '<div style="color:#64748B; font-size:0.75rem; margin-top:0.3rem;">'
                                'This is a fixed example explanation that deliberately downplays a '
                                'critical-risk function, to demonstrate contradiction detection.'
                                '</div>',
                                unsafe_allow_html=True
                            )

                        # Polygraph trust scoring
                        if poly_key not in st.session_state:
                            with st.spinner("Scoring explanation trustworthiness..."):
                                st.session_state[poly_key] = score_explanation(func, st.session_state[cache_key])
                            st.rerun()

                        poly = st.session_state[poly_key]
                        # Determine colors for trust score
                        if poly["trust_score"] >= 70:
                            score_color = "#00CC66"
                            badge_color = "rgba(0, 204, 102, 0.15)"
                            badge_border = "#00CC66"
                        elif poly["trust_score"] >= 45:
                            score_color = "#FF8C00"
                            badge_color = "rgba(255, 140, 0, 0.15)"
                            badge_border = "#FF8C00"
                        else:
                            score_color = "#FF0000"
                            badge_color = "rgba(255, 0, 0, 0.15)"
                            badge_border = "#FF0000"

                        st.markdown(f"""
                        <div style="background:rgba(10,15,28,0.86); border:1px solid rgba(148,163,184,0.16); border-radius:8px; padding:1rem; margin-top:1rem;">
                            <div style="display:flex; align-items:center; gap:1.5rem; margin-bottom:0.8rem;">
                                <div style="font-size:2.6rem; font-weight:900; color:{score_color}; font-variant-numeric:tabular-nums;">{poly['trust_score']:.0f}</div>
                                <div style="font-size:0.72rem; text-transform:uppercase; color:#94A3B8; font-weight:700;">Trust Score</div>
                                <div style="margin-left:auto; background:{badge_color}; border:1px solid {badge_border}; border-radius:999px; padding:0.3rem 0.7rem; font-size:0.75rem; font-weight:900; color:{score_color};">{poly['verdict']}</div>
                            </div>
                            <div style="display:grid; gap:0.5rem;">
                                <div><div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#94A3B8; font-weight:700; margin-bottom:0.2rem;"><span>Consistency</span><span>{poly['consistency_score']:.0f}/100</span></div>
                                <div style="background:#1E293B; border-radius:4px; height:6px; overflow:hidden;"><div style="width:{poly['consistency_score']:.0f}%; background:#38BDF8; height:100%; border-radius:4px;"></div></div></div>
                                <div><div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#94A3B8; font-weight:700; margin-bottom:0.2rem;"><span>Grounding</span><span>{poly['grounding_score']:.0f}/100</span></div>
                                <div style="background:#1E293B; border-radius:4px; height:6px; overflow:hidden;"><div style="width:{poly['grounding_score']:.0f}%; background:#00CC66; height:100%; border-radius:4px;"></div></div></div>
                                <div><div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#94A3B8; font-weight:700; margin-bottom:0.2rem;"><span>Sentiment</span><span>{poly['sentiment_score']:.0f}/100</span></div>
                                <div style="background:#1E293B; border-radius:4px; height:6px; overflow:hidden;"><div style="width:{poly['sentiment_score']:.0f}%; background:#A855F7; height:100%; border-radius:4px;"></div></div></div>
                                <div><div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#94A3B8; font-weight:700; margin-bottom:0.2rem;"><span>Confidence</span><span>{poly['confidence_score']:.0f}/100</span></div>
                                <div style="background:#1E293B; border-radius:4px; height:6px; overflow:hidden;"><div style="width:{poly['confidence_score']:.0f}%; background:#FF8C00; height:100%; border-radius:4px;"></div></div></div>
                            </div>
                            {f'<div style="color:#94A3B8; font-size:0.8rem; margin-top:0.7rem; line-height:1.35;">{poly["reason"]}</div>' if poly["verdict"] in ("FLAG", "REVIEW") else ''}
                        </div>
                        """, unsafe_allow_html=True)

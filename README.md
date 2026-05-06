# CodeScope 🔬

AI-powered code quality analyzer combining deterministic static analysis with LLM-generated reports for non-technical stakeholders.

## Motivation

CodeScope addresses a critical gap in code quality analysis: making technical metrics accessible to non-technical stakeholders while maintaining rigor and trustworthiness.

Key design principles:
*   **Deterministic Ground Truth:** While LLMs are powerful, they are prone to hallucination. CodeScope tethers LLM reasoning directly to hard, deterministic software metrics to ensure trustworthiness.
*   **The "Shift Up" Approach:** Translating dense technical metrics (like cyclomatic complexity and maintainability indices) into accessible business language tailored for CTOs and engineering managers.
*   **Aligning with Industry Standards:** Referencing core tenets from Heitlager et al. (2007) "A Practical Model for Measuring Maintainability", ISO 25010 standards, and the conceptual framing of SIG's Sigrid MCP architecture.

## Architecture

CodeScope operates on a modular, 4-layer pipeline to process source code into executive reports:

1.  **Static Analysis Layer (Lizard + Radon)** — Extracts core deterministic metrics from Python and Java code (NLOC, Complexity, Parameters, Tokens, Maintainability Index, and Grades).
2.  **Risk Scoring Layer** — Prioritizes findings using a weighted heuristic formula combining complexity, size, parameters, and maintainability scores to rank the riskiest functions.
3.  **LLM Report Generation Layer (Gemini API)** — Compiles the flagged functions and their actual source code snippets into grounded, evidence-based reports using strict anti-hallucination system prompt constraints.
4.  **Presentation Layer (Streamlit)** — Surfaces the data via an interactive dashboard displaying metrics visualizations alongside the generated AI reports.

```text
┌──────────────┐      ┌─────────────────────────┐      ┌─────────────────────┐
│ Source Code  │───>│ 1. Static Analysis Layer  │───>│ 2. Risk Scoring Layer │
│ (.py, .java) │      │   (Lizard & Radon)      │      │   (Heuristic Logic) │
└──────────────┘      └─────────────────────────┘      └─────────────────────┘
                                                                  │
                                                                  ▼
┌──────────────────┐  ┌─────────────────────────┐      ┌─────────────────────┐
│ User Dashboard   │<───│ 4. Presentation Layer │<───│ 3. LLM Report Layer │
│ (Streamlit App)  │  │   (Metrics & UI)        │      │   (Gemini API)      │
└──────────────────┘  └─────────────────────────┘      └─────────────────────┘
```

## Key Design Decisions

*   **Grounded Explanations:** The LLM is explicitly forced to reference specific file paths, function names, and line numbers. It cannot make claims without verifiable evidence.
*   **Anti-Hallucination Measures:** The system prompt rigidly forbids the LLM from inventing or hallucinating code, file names, or metrics not present in the ingested static analysis data.
*   **Prompt Engineering Comparison:** An integrated comparison tool runs two prompting strategies side-by-side. This demonstrates directly how grounding instructions and proper context injection vastly improve report quality over "basic" generic AI prompts.
*   **Multi-language Support:** Lizard enables structural analysis across both Python and Java natively.

## Tech Stack

*   **Python 3**
*   **Lizard** (Multi-language metrics)
*   **Radon** (Maintainability indices and complexity grading)
*   **Google Gemini API** (LLM reporting engine)
*   **Streamlit** (Frontend UI)
*   **Pandas** (Data manipulation and structuring)

## How to Run

1. Clone this repository or download the source code:
   ```bash
   git clone <repository_url>
   cd CodeScope
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment:
   *   Open the `.env` file and replace `GEMINI_API_KEY=your-key-here` with your actual Google Gemini API key.
5. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## Example Output

When run on a popular real-world codebase like the `requests` library, CodeScope accurately filters hundreds of functions to highlight structural bottlenecks. For example, it identified:
*   `resolve_redirects` (Complexity: 15, LOC: 81)
*   `send` (Complexity: 19, LOC: 81)
*   `_encode_files` (Complexity: 21, Grade: D)

The pipeline automatically flags these as critical risks and subsequently generates actionable refactoring recommendations mapped directly to business impact (e.g., maintenance cost, bug risk during critical network operations).

## Future Work

*   **Git Churn Integration:** Implement hotspot analysis combining code complexity with change frequency/commit history (mirroring approaches by CodeScene and SIG).
*   **Retrieval-Augmented Generation (RAG):** RAG over SIG's rule descriptions and ISO 25010 documentation to provide even richer, context-aware explanations.
*   **MCP Server Integration:** Build connecting layers to IDE-based coding assistants, mirroring Sigrid's MCP architecture to surface findings directly to developers as they type.
*   **Expanded Language Support:** Leverage Lizard's underlying capacity to support 30+ programming languages.
*   **Automated CI/CD Integration:** Output results into SARIF format for native integration into GitHub Advanced Security or GitLab.
*   **Agent-Based Follow-Up:** Implement conversational drill-downs so users can ask the LLM further questions about specific identified risks iteratively.

## References

*   Heitlager, Kuipers & Visser (2007), *"A Practical Model for Measuring Maintainability"*
*   SIG/TÜViT Evaluation Criteria for Trusted Product Maintainability
*   ISO/IEC 25010 Software Quality Model
*   SIG Sigrid Documentation: [docs.sigrid-says.com](https://docs.sigrid-says.com)
*   Jaoua et al. (2025), *"Combining LLMs with Static Analyzers for Code Review Generation"*

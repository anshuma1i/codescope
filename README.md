# CodeScope

A code quality analysis tool that scans a repository, identifies risky functions, generates AI explanations for non-technical managers, and scores the trustworthiness of those explanations.

## The Problem

Static analysis tools (Lizard, Radon) produce deterministic metrics — cyclomatic complexity, lines of code, maintainability index — that developers understand but managers don't. AI can translate those numbers into plain English, bridging the gap between technical findings and business decisions.

But AI explanations can be confidently wrong. A model can describe a critical-risk function as "straightforward and simple" without contradicting any metric, and no existing tool checks for this. SIG's Sigrid offers AI Explanations but has no trust layer. That's the gap CodeScope addresses with Polygraph — a trust scorer that verifies each explanation against the data it claims to represent.

## How It Works

1. **Scan** — point CodeScope at a local directory or GitHub URL. It runs Lizard and Radon across every Python and Java file to extract cyclomatic complexity, lines of code, maintainability index, function boundaries, and parameter counts.

2. **Score** — each function is ranked by a weighted risk formula that combines complexity, NLOC, and maintainability into a 0–100 risk score. Functions are bucketed into Critical, High, Moderate, or Low.

3. **Explain** — the top-N riskiest functions are fed to Gemini 2.5 Flash with a grounded prompt that forces the model to mention the real function name, file, complexity number, and risk level. The output is a manager-friendly paragraph explaining why the function matters and what should be done.

4. **Polygraph** — each explanation is run through four independent trust checks. The model is re-queried multiple times, the explanation is scanned for facts, sentiment, and hedging, and everything is combined into a single trust score.

5. **Display** — the Streamlit UI shows a trust score (0–100), four sub-score bars, a verdict (TRUST / REVIEW / FLAG), and a reason sentence identifying the weakest dimension.

## Polygraph — The Trust Scorer

Polygraph runs four checks on every explanation. Each produces a 0–100 score; they are weighted and combined.

- **Self-consistency (20%)** — the model is asked to explain the same function three more times. All four explanations (including the original) are compared pairwise using word overlap, with function names and file names stripped to avoid artificially inflating agreement. Low consistency means the model is improvising rather than reasoning from fixed data.

- **Grounding (30%)** — checks whether the explanation mentions the real function name, file basename, complexity value, and risk level. A generic explanation that could describe any function scores zero.

- **Sentiment alignment (35%)** — checks whether the explanation's tone matches the function's actual risk level. Critical and high-risk functions should sound urgent (words like "dangerous", "must", "failure"). Low-risk functions should sound reassuring ("straightforward", "robust", "unlikely"). Contradictions — a critical function described as "manageable" — are penalized heavily. Moderate-risk functions are treated as neutral.

- **Confidence (15%)** — counts hedging language ("might", "seems", "possibly"). Each hedge costs 20 points. Low weight because hedging is a crude proxy.

The verdict thresholds are fixed: TRUST ≥ 70, REVIEW ≥ 45, FLAG < 45.

### Proven by contradiction test

| Scenario | Verdict | Sentiment | Trust Score |
|---|---|---|---|
| Low risk + reassuring explanation | TRUST | 100/100 | 83.3 |
| Critical risk + honest explanation | TRUST | 100/100 | 76.9 \* |
| Critical risk + reassuring explanation | FLAG | 0/100 | 33.4 |

\*Scores vary slightly between runs due to the sampling-based consistency check.

The third row is the key test — a deliberately contradictory explanation that any human reader would spot as wrong. Polygraph catches it. The first two rows confirm that Polygraph does not produce false alarms when the explanation is honest.

## The Research Direction

The current Polygraph uses sampling-based proxies — it infers trustworthiness from output patterns rather than reading the model's internals. The frontier is Natural Language Autoencoders (Fraser-Taliente et al., 2026), a technique from Anthropic that reads a model's internal activations at a specific layer and produces human-readable explanations of what the model is representing internally. The paper also demonstrates NLAs catching unverbalized evaluation awareness — cases where a model internally suspects it is being tested without saying so — which is directly relevant to the trust problem Polygraph addresses. A production version of Polygraph would move from output sampling to activation-based detection, catching fabrication at the source rather than inferring it statistically.

## Stack

- Python 3.9
- Streamlit (UI)
- Google Gemini 2.5 Flash (LLM)
- Lizard (complexity metrics)
- Radon (maintainability index)

## Run It

```bash
git clone https://github.com/anshuma1i/codescope.git
cd codescope
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env
streamlit run app.py
```

## References

Fraser-Taliente, K., Kantamneni, S., Ong, E., Mossing, D., et al. (2026). *Natural Language Autoencoders Produce Unsupervised Explanations of LLM Activations.* Anthropic. https://transformer-circuits.pub/2026/nla/

Neuronpedia NLA Explorer (2026). Interactive demo of NLA explanations on Llama 3.3 70B. https://www.neuronpedia.org/llama3.3-70b-it/nla

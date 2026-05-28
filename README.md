<a id="top"></a>

<div align="center">
  <h1>LabHorizon</h1>
</div>

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-CongLab--Research%2FLabHorizon-000000?logo=github&logoColor=white)](https://github.com/CongLab-Research/LabHorizon)&nbsp;
[![HF Level 1](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-Level%201%203D%20Assets-blue)](https://huggingface.co/datasets/CongLab-Research/LabHorizon-3D-Asset-Perception)&nbsp;
[![HF Level 2](https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-Level%202%20Planning-purple)](https://huggingface.co/datasets/CongLab-Research/LabHorizon-Protocol-Conditioned-Planning)&nbsp;
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)&nbsp;
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

**Enhancing Laboratory 3D Perception and Long-Horizon Planning via Protocol-Conditioned Action Prediction.**

[Overview](#overview) | [Datasets](#datasets) | [Evaluation](#evaluation) | [Quick Start](#quick-start) | [Citation](#citation)

</div>

---

## Overview

**LabHorizon** is a data and evaluation suite for laboratory action prediction. It studies how models connect multi-view laboratory assets, real-world experimental context, and long-horizon action structure before they can support reliable AI scientist workflows.

Unlike general scientific QA or diagram-based multimodal benchmarks, LabHorizon frames laboratory reasoning as **protocol-conditioned action prediction**: a model must either select the next protocol-consistent action from visually grounded candidates or produce a structured long-horizon experimental action sequence.

### Highlights

<table>
<tr>
<td align="center" width="25%">3D<br/><b>Asset Perception</b><br/><sub>Multi-view laboratory asset inputs</sub></td>
<td align="center" width="25%">Protocol<br/><b>Action Prediction</b><br/><sub>History and protocol context guide the next action</sub></td>
<td align="center" width="25%">Planning<br/><b>Long Horizon</b><br/><sub>Structured action sequences with dependencies</sub></td>
<td align="center" width="25%">AST<br/><b>Programmatic Scoring</b><br/><sub>Action, parameter, and dependency parsing</sub></td>
</tr>
<tr>
<td align="center">Train<br/><b>3,000 + 3,000</b><br/><sub>Training samples across two levels</sub></td>
<td align="center">Test<br/><b>200 + 200</b><br/><sub>Matched evaluation samples</sub></td>
<td align="center">API<br/><b>OpenAI-Compatible</b><br/><sub>Works with OpenRouter and similar endpoints</sub></td>
<td align="center">Cache<br/><b>Resume Friendly</b><br/><sub>JSONL outputs can be reused across runs</sub></td>
</tr>
</table>

### Data and Evaluation Flow

```mermaid
flowchart LR
    A["Laboratory assets<br/>multi-view images"] --> L1["Level 1<br/>next-action prediction"]
    P["Real-world protocol context"] --> L1
    P --> L2["Level 2<br/>long-horizon planning"]
    AP["Action pool<br/>function-call interface"] --> L2
    L1 --> S1["Next-action accuracy"]
    L2 --> AST["Python AST parser"]
    AST --> S2["Action Sequence Similarity"]
    AST --> S3["Parameter Accuracy"]

    style A fill:#e0f2fe,stroke:#0284c7,stroke-width:2px
    style P fill:#ecfccb,stroke:#65a30d,stroke-width:2px
    style L1 fill:#fef3c7,stroke:#d97706,stroke-width:2px
    style L2 fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px
    style AST fill:#fee2e2,stroke:#dc2626,stroke-width:2px
```

## Datasets

| Level | Hugging Face Dataset | Input | Target | Metric |
|:---|:---|:---|:---|:---|
| **Level 1** | [LabHorizon-3D-Asset-Perception](https://huggingface.co/datasets/CongLab-Research/LabHorizon-3D-Asset-Perception) | Three asset views, historical actions, candidate next actions | Gold next action | Next-action accuracy |
| **Level 2** | [LabHorizon-Protocol-Conditioned-Planning](https://huggingface.co/datasets/CongLab-Research/LabHorizon-Protocol-Conditioned-Planning) | Context, goal, constraints, available inputs, action pool | Gold experimental action sequence | Action Sequence Similarity, Parameter Accuracy |

### Level 1 Schema

| Column | Meaning |
|:---|:---|
| `id` | Stable public sample identifier, such as `LabHorizon-L1-test-000001`. |
| `asset` | Three rendered views of the same laboratory asset. |
| `historical_actions` | Previous protocol actions and the current experimental state. |
| `candidate_next_actions` | Candidate next laboratory actions. |
| `reasoning` | Reference reasoning for the gold next action. |
| `next_action` | Gold protocol-consistent next action. |
| `asset_name` | Human-readable asset name for analysis. |
| `asset_family` | Asset family label for distribution analysis. |

### Level 2 Schema

| Column | Meaning |
|:---|:---|
| `id` | Stable public sample identifier, such as `LabHorizon-L2-test-000001`. |
| `context` | Experimental context for the local protocol window. |
| `goal` | Planning objective. |
| `constraints` | Protocol-derived constraints and parameter requirements. |
| `available_inputs` | Raw materials, samples, or measurements available before planning. |
| `action_pool_names` | Names of available action-pool functions. |
| `action_pool` | Python function definitions describing available laboratory actions. |
| `gold_action_sequence` | Gold long-horizon experimental action sequence. |

## Evaluation

The evaluator keeps model interaction simple and model-agnostic. It sends natural-language prompts to an OpenAI-compatible chat completions endpoint, stores raw model outputs as JSONL, and computes metrics locally.

### Level 1: Next-Action Prediction

Level 1 prompts contain asset images, historical actions, and candidate next actions. The model is asked to reason first and end with:

```text
Final Next Action: X
```

`X` may be a candidate letter or the exact candidate action. The evaluator maps the final response back to the candidate list and reports `next_action_accuracy`.

### Level 2: Protocol-Conditioned Planning

Level 2 prompts contain a real-world experimental context, constraints, available inputs, and an action pool. The model may answer in natural language, but the structured action sequence must appear as Python-style function calls, usually inside a fenced code block:

```python
lysate = lyse_cells(sample=cell_pellet, buffer=lysis_buffer, duration_min=10)
clarified = centrifuge(sample=lysate, speed_x_g=12000, duration_min=15)
```

The evaluator uses Python AST to extract action calls, keyword parameters, assigned intermediate variables, and variable dependencies. It reports:

| Metric | What It Measures |
|:---|:---|
| `Action Sequence Similarity` | Whether predicted actions appear at the correct positions relative to the gold sequence. |
| `Parameter Accuracy` | Whether aligned actions use correct parameter keys, values, raw inputs, and generated-variable dependencies. |
| `Final Score` | The mean of Action Sequence Similarity and Parameter Accuracy. |

## Quick Start

### 1. Clone Code and Data

The recommended local layout keeps code and datasets as sibling repositories:

```bash
mkdir -p LabHorizon/code LabHorizon/data

git clone https://github.com/CongLab-Research/LabHorizon \
  LabHorizon/code/LabHorizon

git clone https://huggingface.co/datasets/CongLab-Research/LabHorizon-3D-Asset-Perception \
  LabHorizon/data/LabHorizon-3D-Asset-Perception

git clone https://huggingface.co/datasets/CongLab-Research/LabHorizon-Protocol-Conditioned-Planning \
  LabHorizon/data/LabHorizon-Protocol-Conditioned-Planning

cd LabHorizon/code/LabHorizon
```

### 2. Install

```bash
python -m pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Fill `.env` with an OpenAI-compatible endpoint:

```text
BASE_URL=https://openrouter.ai/api/v1
API_KEY=your_api_key_here
```

Do not commit `.env`. It is ignored by default.

### 4. Run Level 1 Evaluation

```bash
python -m evaluation.level1.evaluate \
  --split test \
  --model openai/gpt-5.4 \
  --output results/level1_gpt54.jsonl
```

### 5. Run Level 2 Evaluation

```bash
python -m evaluation.level2.evaluate \
  --split test \
  --model openai/gpt-5.4 \
  --output results/level2_gpt54.jsonl
```

Each command writes one JSONL row per evaluated sample plus a `.summary.json` file. Use `--resume` to reuse already written rows after interruption.

## Useful Options

```bash
python -m evaluation.level1.evaluate --help
python -m evaluation.level2.evaluate --help
```

| Option | Default | Purpose |
|:---|:---|:---|
| `--data-root` | `../../data` | Directory containing the two Hugging Face dataset clones. |
| `--cache-dir` | `.cache/huggingface/datasets` | Local Hugging Face dataset cache. |
| `--limit` | unset | Evaluate only the first N examples. |
| `--resume` | `False` | Reuse existing JSONL rows in `--output`. |
| `--temperature` | unset | Optional model temperature. |
| `--timeout` | `120` | HTTP timeout in seconds. |
| `--retries` | `2` | API retry count. |

## Project Structure

```text
LabHorizon/
├── README.md
├── LICENSE
├── requirements.txt
├── .env.example
└── evaluation/
    ├── utils.py                  # OpenAI-compatible client, dataset loading, JSONL cache
    ├── level1/
    │   ├── prompts.py            # Multi-image next-action prompts and answer parsing
    │   └── evaluate.py           # Level 1 evaluation entry point
    └── level2/
        ├── prompts.py            # Protocol-conditioned planning prompts
        ├── metrics.py            # AST parsing and ASS / PA metrics
        └── evaluate.py           # Level 2 evaluation entry point
```

Generated outputs should go under `results/`, which is ignored by default.

## Roadmap

- Release paper metadata and citation after the manuscript is public.
- Add official model results and analysis tables.
- Add agent and fine-tuned model evaluation scripts when checkpoints are released.

## Citation

```bibtex
@misc{labhorizon2026,
  title = {LabHorizon: Enhancing Laboratory 3D Perception and Long-Horizon Planning via Protocol-Conditioned Action Prediction},
  author = {CongLab Research},
  year = {2026},
  url = {https://github.com/CongLab-Research/LabHorizon}
}
```

## Contact

Please open a GitHub issue for reproducibility questions, dataset access problems, or evaluator bugs.

## Star History

<a href="https://www.star-history.com/?repos=CongLab-Research%2FLabHorizon&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=CongLab-Research/LabHorizon&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=CongLab-Research/LabHorizon&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/image?repos=CongLab-Research/LabHorizon&type=date&legend=top-left" />
 </picture>
</a>

<p align="right"><a href="#top">Back to top</a></p>

# LabHorizon

Evaluation code for the LabHorizon Level 1 and Level 2 datasets.

## Repository Layout

Expected local layout:

```text
LabHorizon/
  data/
    LabHorizon-3D-Asset-Perception/
    LabHorizon-Protocol-Conditioned-Planning/
  code/
    LabHorizon/
      evaluation/
        utils.py
        level1/
        level2/
```

The `data/` repositories are Hugging Face dataset clones:

- https://huggingface.co/datasets/CongLab-Research/LabHorizon-3D-Asset-Perception
- https://huggingface.co/datasets/CongLab-Research/LabHorizon-Protocol-Conditioned-Planning

## Setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`:

```text
BASE_URL=https://openrouter.ai/api/v1
API_KEY=your_api_key_here
```

`BASE_URL` must point to an OpenAI-compatible chat completions endpoint root, for example `https://openrouter.ai/api/v1`.

## Level 1 Evaluation

```bash
python -m evaluation.level1.evaluate \
  --split test \
  --model openai/gpt-5.4 \
  --output results/level1_gpt54.jsonl
```

Level 1 sends historical actions, candidate next actions, and three asset images to the model. The evaluator parses `Final Next Action: X` and reports next-action accuracy.

## Level 2 Evaluation

```bash
python -m evaluation.level2.evaluate \
  --split test \
  --model openai/gpt-5.4 \
  --output results/level2_gpt54.jsonl
```

Level 2 sends the experiment context, constraints, available inputs, and action pool. The model may answer in natural language, but the evaluator extracts a structured action sequence from a Python fenced block or assignment-style lines, then computes:

- `Action Sequence Similarity`
- `Parameter Accuracy`
- `Final Score = (ASS + PA) / 2`

## Useful Options

```bash
python -m evaluation.level1.evaluate --help
python -m evaluation.level2.evaluate --help
```

Common options:

- `--data-root`: defaults to `../../data` relative to this repository.
- `--cache-dir`: defaults to `.cache/huggingface/datasets` inside this repository.
- `--limit`: evaluate only the first N examples.
- `--resume`: reuse already written JSONL rows in `--output`.
- `--temperature`: optional API temperature.
- `--timeout`: HTTP timeout in seconds.

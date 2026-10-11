# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

An entry for the Kaggle competition "Google - The Gemma 4 Developer Agent" (https://www.kaggle.com/competitions/gemma-4-developer-agent). The deliverable is not Python code but a **declarative Google ADK agent config** (YAML + Markdown prompts, optionally LoRA adapters) that Kaggle runs on `gemma-4-31b-it-qat-w4a16-ct` to fix SWE-bench-style Python issues. Score = fraction of ~120 hidden tasks whose hidden tests pass.

**Read `NOTES.md` first**: it holds the competition rules, limits, scoring-environment facts and harness gotchas. Update it when you learn something new rather than duplicating facts here. The authoritative harness spec is `data/HARNESS_README.md`.

## Commands

All Python runs through the project venv (Python 3.12, CPU torch, official harness wheels installed):

```bash
# Download data (everything except repo snapshots, ~0.9 GB), plus specific task snapshots
./scripts/download_data.sh httpx_3672 rich_3061      # --all for the full 22 GB

# Validate + compile an agent with the official harness, write submissions/<name>.zip
# and notebooks/<name>/ (the Kaggle submit notebook)
.venv/bin/python scripts/build_submission.py agents/baseline_v1

# Grade patches locally with the real Phase 2 verifier (needs Docker image swebench-sandbox:latest)
.venv/bin/python scripts/verify_patches.py --mode gold rich_3061          # reference patch, should pass
.venv/bin/python scripts/verify_patches.py --mode empty rich_3061         # no patch, should fail
.venv/bin/python scripts/verify_patches.py --mode dir --patch-dir runs/x/patches <ids>

# Rebuild the sandbox image
docker build -t swebench-sandbox:latest -f data/docker/Dockerfile.sandbox data/docker

# Submit (only with explicit user approval each time: 1 submission/day, ~33 h scoring queue)
kaggle kernels push -p notebooks/<name>
kaggle competitions submit gemma-4-developer-agent -k dophuchung/g4-agent-<name> -f submission.zip -v <version> -m "<msg>"
kaggle competitions submissions gemma-4-developer-agent
```

There is no local GPU, so agent runs (Phase 1, model inference) cannot happen on this machine; they need Kaggle L4x4 notebooks or rented GPUs. Locally we can only validate configs and grade patches.

## Architecture

- `agents/<name>/` — one directory per agent version; its contents are exactly the root of `submission.zip`. Required `agent.yaml`; optional `eval_config.yaml` (per-task budgets), `prompts/*.md` and `configs/*.yaml` pulled in via `!include`, `sub_agents/*.yaml`, `skills/<n>/SKILL.md`, `adapters/<n>/` (PEFT safetensors). Only `.yaml .yml .md .txt .py .json .safetensors` are allowed. Create a new directory per experiment instead of editing a submitted one, so leaderboard scores stay traceable.
- `scripts/build_submission.py` — mirrors Kaggle's checks (extension whitelist, size, `validate_directory`, single-model check, `compile_submission` with stub tools) and generates a CPU notebook that embeds the agent's text files and writes `/kaggle/working/submission.zip`. Kaggle reruns that notebook on submit. Agents with `adapters/` are not supported yet: the weights must go into a Kaggle dataset attached to the notebook.
- `scripts/verify_patches.py` — instantiates the real `swegemma.evaluate.Evaluator` and monkeypatches `_run_agent_sandbox` to return a fixed patch, so grading is identical to Kaggle's Phase 2 (fresh container, apply patch, reset test files, apply `test_patch`, pytest + JUnit validation). Results go to `runs/verify_<mode>/`.
- Harness source (useful for answering "what does Kaggle actually do"): `.venv/lib/python3.12/site-packages/{swegemma,adk_submission,adk_eval_core}`. Kaggle's `scripts/inference.py` is not public.
- `data/` (gitignored) — `tasks.jsonl` (129 public tasks incl. reference `patch` and `test_patch`), `snapshots/`, `graphs/`, `embeddings/`, `wheels/`, `sample_submission/`, `docker/`.
- `reference/` (gitignored) — pulled public notebooks, forum threads, harness wheels.

## Constraints that shape agent design

- Instructions are ADK templates: `{identifier}` in a prompt is interpolated from session state and an unknown key crashes the run. Do not put curly-brace placeholders in prompts (build_submission.py warns).
- Per-task budget must keep ~120 sequential tasks under 12 h total, and `timeout_seconds` doubles as the grading pytest timeout (keep >= 300). See `NOTES.md` for the reasoning.
- The public training sandbox cannot grade many tasks even with the gold patch (dependency issues; the hidden set is clean). Only trust local scores on tasks where `--mode gold` passes.
- Hidden tasks come from private repos, so avoid tuning prompts to fastapi/rich/requests/httpx specifics.

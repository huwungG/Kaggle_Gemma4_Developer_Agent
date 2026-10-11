# Competition notes

Facts gathered in Phase 0 (2026-10-11). Sources: competition pages, `data/HARNESS_README.md`,
harness source in `.venv/.../swegemma`, forum threads in `reference/discussions/`.

## Submission limits
- 1 submission/day, plus a pending limit: no new submission while one is still scoring.
  Scoring queue was ~33 h on 2026-10-10, so a submission can cost more than one day.
- Up to 2 final submissions. Final deadline 2026-12-02, entry/merge deadline 2026-11-25.
- Submit = a CPU notebook that writes `/kaggle/working/submission.zip`; Kaggle reruns it, then scores the zip on 4x L4.
- External data and models are allowed if public and low cost (rules section 6). Winners license under Apache 2.0.

## Scoring environment
- Only `gemma-4-31b-it-qat-w4a16-ct`, vLLM TP=4, `max_model_len` 32,768, LoRA up to rank 128, 8 adapters, zip < 3 GiB.
- ~120 hidden tasks from private repos, half public LB / half private. Tasks run sequentially; whole run must finish in 12 h
  including sandbox setup. Forum calibration: <= ~5.5 min per task is safe. A run that exceeds 12 h errors out.
- `eval_config.yaml` `timeout_seconds` is also the Phase 2 pytest timeout (`swegemma/harness/verification.py:638`). Keep >= 300.
- The working tree is graded even without `submit_patch()`. Edits to test files and test config are discarded before grading.
- Sandbox: offline, 4 GB RAM, 2 vCPU, no `rg`/`tree`.

## Tool gotchas
- `search_similar_code` returns full node source with no cap (100k+ chars for big classes): it can overflow context and lose the task. Avoid.
- Code graphs only have lowercase `calls` edges and no async functions. `get_code_neighbors(edge_type="CALLS")` returns nothing.
- `include_thoughts: false` no longer disables thinking in wheelhouse v29/v30; `thinking_budget: 0` does.
- Sample submission: 1 min / 10 tool calls budget, and its LoRA adapters are all-zero no-ops.

## Local setup
- No local GPU: agent runs need Kaggle L4x4 notebooks (2x GPU quota) or rented GPUs.
- `.venv` (Python 3.12, CPU torch) has the official harness: `swegemma` 0.2.11, `adk_submission` 0.2.13, `google-adk` 1.36.1.
- Docker image `swebench-sandbox:latest` built from `data/docker/Dockerfile.sandbox`.
- `scripts/verify_patches.py` grades patches with the real Phase 2 verifier.
  Training-set sandbox is broken for many tasks (host-confirmed; hidden set is clean): gold patch passes `rich_3061`
  but fails `httpx_3672` (old httpx wheel shadows repo), `requests_6592` (httpbin fixture), `fastapi_14077`
  (missing `typing_inspection`). Need a gold-pass subset before trusting local scores.

## Scripts
- `scripts/download_data.sh [ids...]` data except snapshots (~0.9 GB) plus named snapshots; `--all` for 22 GB.
- `scripts/build_submission.py agents/<name>` validate + compile with the harness, write `submissions/<name>.zip`
  and `notebooks/<name>/` (submit notebook).
- `scripts/verify_patches.py --mode gold|empty|dir ids...`

## Submission log
| Date (UTC) | Ref | Agent | Kernel version | Public LB | Notes |
|---|---|---|---|---|---|
| 2026-10-11 | 57066712 | agents/baseline_v1 | g4-agent-baseline-v1 v1 | pending | single agent, 4 min / 40 calls, no search_similar_code |

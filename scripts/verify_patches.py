"""Grade patches locally with the official Phase 2 verifier (Docker, no GPU needed).

Replaces the agent phase with a fixed patch, then runs swegemma's real verification
(fresh container, apply patch, reset tests, apply test_patch, pytest + JUnit checks).

Usage:
    .venv/bin/python scripts/verify_patches.py --mode gold  httpx_3672 rich_3061
    .venv/bin/python scripts/verify_patches.py --mode empty httpx_3672
    .venv/bin/python scripts/verify_patches.py --mode dir --patch-dir runs/x/patches httpx_3672

Modes:
    gold   reference `patch` from tasks.jsonl (should resolve; checks the sandbox works)
    empty  no patch (should fail; checks the tests really test the bug)
    dir    <patch-dir>/<instance_id>.patch, e.g. patches from a Kaggle run
"""

import argparse
import asyncio
import json
from pathlib import Path

from adk_submission import ModelRegistry
from swegemma.config import EvalConfig
from swegemma.evaluate import Evaluator
from swegemma.models import load_tasks

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_ids", nargs="*", help="default: every task with a downloaded snapshot")
    ap.add_argument("--mode", choices=["gold", "empty", "dir"], default="gold")
    ap.add_argument("--patch-dir", type=Path)
    ap.add_argument("--results-dir", type=Path)
    ap.add_argument("--timeout", type=int, default=300, help="pytest timeout; matches eval_config timeout_seconds")
    args = ap.parse_args()

    tasks = {t.instance_id: t for t in load_tasks(DATA / "tasks.jsonl")}
    ids = args.task_ids or sorted(p.name.removesuffix(".tgz") for p in (DATA / "snapshots").glob("*.tgz"))
    results_dir = args.results_dir or ROOT / "runs" / f"verify_{args.mode}"

    config = EvalConfig(
        tasks_path=DATA / "tasks.jsonl",
        snapshots_dir=DATA / "snapshots",
        results_dir=results_dir,
        submission_dir=ROOT / "agents" / "baseline_v1",
        models=ModelRegistry(),
        sandbox="docker",
        wheels_dir=DATA / "wheels",
        graph_dir=str(DATA / "graphs"),
        embeddings_dir=str(DATA / "embeddings"),
        timeout_seconds=args.timeout,
        display_mode="quiet",
    )
    evaluator = Evaluator(config)

    def patch_for(task) -> str:
        if args.mode == "gold":
            return task.patch
        if args.mode == "dir":
            p = args.patch_dir / f"{task.instance_id}.patch"
            return p.read_text() if p.exists() else ""
        return ""

    async def fixed_patch(task, *_a, **_kw):
        return patch_for(task), None, None

    evaluator._run_agent_sandbox = fixed_patch

    results_dir.mkdir(parents=True, exist_ok=True)
    resolved = 0
    for i, iid in enumerate(ids, 1):
        r = asyncio.run(evaluator.evaluate_task(task=tasks[iid], task_index=i, total_tasks=len(ids)))
        resolved += bool(r.resolved)
        print(f"[{i}/{len(ids)}] {iid}: resolved={r.resolved} exit={r.test_exit_code} "
              f"{r.duration_seconds:.0f}s {('error=' + r.error[:200]) if r.error else ''}", flush=True)
        (results_dir / f"{iid}.log").write_text(r.test_output or "")
        with open(results_dir / "results.jsonl", "a") as f:
            f.write(json.dumps({"id": iid, "mode": args.mode, "resolved": r.resolved,
                                "exit": r.test_exit_code, "error": r.error}) + "\n")
    print(f"{resolved}/{len(ids)} resolved ({args.mode})")


if __name__ == "__main__":
    main()

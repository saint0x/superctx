#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/deepsaint/Desktop/superctx")
ARENA = ROOT / "arena"
RUNS = ARENA / "runs"
DEFAULT_MODELS = [
    "poolside/laguna-xs.2:free",
    "poolside/laguna-m.1:free",
    "nvidia/nemotron-3-super:free",
    "openai/gpt-oss-120b:free",
    "z-ai/glm-4.5-air:free",
]
INTER_RUN_SLEEP_SECS = float(os.environ.get("SUPERCTX_SWEEP_SLEEP_SECS", "8"))


def parse_models(argv: list[str]) -> list[str]:
    if argv:
        return argv
    env_models = os.environ.get("SUPERCTX_SWEEP_MODELS", "")
    if env_models.strip():
        return [item.strip() for item in env_models.split(",") if item.strip()]
    return DEFAULT_MODELS


def run_one(model: str) -> dict:
    env = os.environ.copy()
    env["SUPERCTX_MODEL_PROVIDER"] = "openrouter"
    env["OPENROUTER_MODEL"] = model
    proc = subprocess.run(
        [sys.executable, str(ARENA / "eval_model.py")],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    stdout_text = proc.stdout.strip()
    stdout = stdout_text.splitlines()
    summary = None
    for start in range(len(stdout_text) - 1, -1, -1):
        if stdout_text[start] != "{":
            continue
        candidate = stdout_text[start:].strip()
        try:
            summary = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if summary is None:
        raise RuntimeError(f"no run summary for {model}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    summary["returncode"] = proc.returncode
    summary["stdout_tail"] = stdout[-20:]
    summary["stderr"] = proc.stderr[-4000:]
    return summary


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("missing OPENROUTER_API_KEY")
    models = parse_models(sys.argv[1:])
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = RUNS / f"{ts}-openrouter-sweep"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, model in enumerate(models):
        if index:
            time.sleep(INTER_RUN_SLEEP_SECS)
        print(f"running {model}", flush=True)
        started = time.time()
        try:
            result = run_one(model)
            result["duration_secs"] = round(time.time() - started, 2)
        except Exception as exc:
            result = {
                "provider": "openrouter",
                "model": model,
                "run_dir": "",
                "passed": 0,
                "total": 0,
                "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "returncode": 1,
                "duration_secs": round(time.time() - started, 2),
                "error": str(exc),
            }
        results.append(result)
        print(json.dumps(result, indent=2), flush=True)

    leaderboard = sorted(
        results,
        key=lambda item: (
            item.get("passed", 0),
            -item.get("token_usage", {}).get("total_tokens", 0),
        ),
        reverse=True,
    )
    payload = {"models": models, "results": results, "leaderboard": leaderboard}
    (out_dir / "openrouter_sweep.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"sweep_dir": str(out_dir), "leaderboard": leaderboard}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

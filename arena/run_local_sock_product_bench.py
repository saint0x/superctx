#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "arena" / "runs"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    thesis_axis: str
    request: str
    memories: list[dict[str, Any]]
    expected: list[str]
    forbidden: list[str]
    exact: str | None = None
    max_tokens: int = 256


SCENARIOS = [
    Scenario(
        scenario_id="exact_tool_contract",
        thesis_axis="exact-answer discipline",
        request=(
            "Give the exact numeric answer for 183 * 27. Answer with the number only. "
            "Do not explain."
        ),
        memories=[
            {
                "scope": "workspace",
                "kind": "policy",
                "importance": 8,
                "confidence": 9,
                "content": "For exact arithmetic requests, superctx frames require exact output only.",
            }
        ],
        expected=["4941"],
        forbidden=["approximately", "about", "I think"],
        exact="4941",
        max_tokens=192,
    ),
    Scenario(
        scenario_id="local_grounding_paths",
        thesis_axis="local-grounded context selection",
        request=(
            "In two sentences, identify the persistent brain database path and the validator "
            "source path. Cite the exact path strings."
        ),
        memories=[
            {
                "scope": "workspace",
                "kind": "fact",
                "importance": 10,
                "confidence": 10,
                "content": "The persistent brain database path is .brain/brain.db.",
            },
            {
                "scope": "workspace",
                "kind": "fact",
                "importance": 10,
                "confidence": 10,
                "content": "The validator implementation path is src/services/validator.fzy.",
            },
            {
                "scope": "workspace",
                "kind": "distractor",
                "importance": 2,
                "confidence": 2,
                "content": "Wrong stale path: src/validator.ts.",
            },
        ],
        expected=[".brain/brain.db", "src/services/validator.fzy"],
        forbidden=["src/validator.ts", "I cannot"],
        max_tokens=160,
    ),
    Scenario(
        scenario_id="context_budget_under_distractors",
        thesis_axis="memory ranking under distractors",
        request=(
            "Prepare a five-bullet incident handoff. Include the active model, endpoint, "
            "local-first policy, and benchmark objective. Ignore stale provider notes."
        ),
        memories=[
            {
                "scope": "workspace",
                "kind": "fact",
                "importance": 10,
                "confidence": 10,
                "content": "Active model for this bench is Qwen/Qwen3-30B-A3B-GPTQ-Int4.",
            },
            {
                "scope": "workspace",
                "kind": "fact",
                "importance": 10,
                "confidence": 10,
                "content": "Active local sock endpoint is http://127.0.0.1:8000/v1/chat/completions.",
            },
            {
                "scope": "workspace",
                "kind": "policy",
                "importance": 9,
                "confidence": 9,
                "content": "Before web browsing, diagnose local repo and runtime state first.",
            },
            {
                "scope": "workspace",
                "kind": "goal",
                "importance": 9,
                "confidence": 9,
                "content": "Benchmark objective: determine whether superctx improves local-model context use over raw prompting.",
            },
            {
                "scope": "global",
                "kind": "distractor",
                "importance": 1,
                "confidence": 1,
                "content": "Stale provider note: use OpenRouter gpt-oss-20b for this bench.",
            },
            {
                "scope": "global",
                "kind": "distractor",
                "importance": 1,
                "confidence": 1,
                "content": "Stale endpoint note: use http://127.0.0.1:1234.",
            },
        ],
        expected=[
            "Qwen/Qwen3-30B-A3B-GPTQ-Int4",
            "127.0.0.1:8000",
            "local",
            "superctx",
        ],
        forbidden=["OpenRouter", "127.0.0.1:1234"],
        max_tokens=256,
    ),
    Scenario(
        scenario_id="cross_round_recall",
        thesis_axis="durable session/workspace recall",
        request=(
            "What is the release bridge checkpoint phrase? Answer with the phrase only."
        ),
        memories=[
            {
                "scope": "session",
                "kind": "fact",
                "importance": 10,
                "confidence": 10,
                "content": "The release bridge checkpoint phrase is orchid-17.",
            },
            {
                "scope": "workspace",
                "kind": "distractor",
                "importance": 2,
                "confidence": 3,
                "content": "Old checkpoint phrase was cobalt-99.",
            },
        ],
        expected=["orchid-17"],
        forbidden=["cobalt-99"],
        exact="orchid-17",
        max_tokens=192,
    ),
]

SCENARIOS.extend(
    [
        Scenario(
            scenario_id="scoped_workspace_override",
            thesis_axis="scope-aware durable recall",
            request="What is the current workspace codename? Answer with the codename only.",
            memories=[
                {"scope": "workspace", "kind": "fact", "importance": 10, "confidence": 10, "content": "The current workspace codename is marble-harbor."},
                {"scope": "global", "kind": "distractor", "importance": 4, "confidence": 4, "content": "A stale global codename from another project was black-sun."},
            ],
            expected=["marble-harbor"],
            forbidden=["black-sun"],
            exact="marble-harbor",
            max_tokens=96,
        ),
        Scenario(
            scenario_id="canonical_build_contract",
            thesis_axis="local developer contract recall",
            request="Which build command is canonical for this workspace? Answer with the exact command only.",
            memories=[
                {"scope": "workspace", "kind": "policy", "importance": 10, "confidence": 10, "content": "Canonical build command: fz build --backend cranelift"},
                {"scope": "workspace", "kind": "distractor", "importance": 2, "confidence": 2, "content": "Deprecated build command: npm run build."},
                {"scope": "global", "kind": "distractor", "importance": 1, "confidence": 1, "content": "Generic JavaScript projects often use pnpm build."},
            ],
            expected=["fz build --backend cranelift"],
            forbidden=["npm run build", "pnpm"],
            exact="fz build --backend cranelift",
            max_tokens=96,
        ),
        Scenario(
            scenario_id="negative_no_invention",
            thesis_axis="unknown-answer discipline",
            request="What is the secret launch password? If it is not recorded in memory, answer NOT RECORDED exactly.",
            memories=[
                {"scope": "workspace", "kind": "policy", "importance": 10, "confidence": 10, "content": "When a requested credential or secret is not explicitly recorded, answer NOT RECORDED and do not invent it."},
                {"scope": "workspace", "kind": "fact", "importance": 6, "confidence": 8, "content": "Recorded non-secret release phrase: orchid-17."},
            ],
            expected=["NOT RECORDED"],
            forbidden=["orchid-17", "password", "secret is"],
            exact="NOT RECORDED",
            max_tokens=96,
        ),
        Scenario(
            scenario_id="stale_high_noise_conflict",
            thesis_axis="conflict resolution under noisy memory",
            request="Name the active inference server and model family in one sentence. Ignore deprecated notes.",
            memories=[
                {"scope": "workspace", "kind": "fact", "importance": 10, "confidence": 10, "content": "Active inference server is local sock."},
                {"scope": "workspace", "kind": "fact", "importance": 10, "confidence": 10, "content": "Active model family is Qwen3 30B GPTQ."},
                {"scope": "workspace", "kind": "distractor", "importance": 9, "confidence": 1, "content": "Deprecated high-visibility note: active server is OpenRouter running GPT-OSS."},
                {"scope": "global", "kind": "distractor", "importance": 8, "confidence": 1, "content": "Old hosted inference path used Anthropic Claude."},
            ],
            expected=["sock", "Qwen3", "30B"],
            forbidden=["OpenRouter", "GPT-OSS", "Claude"],
            max_tokens=160,
        ),
        Scenario(
            scenario_id="ordered_recovery_runbook",
            thesis_axis="format and operations discipline",
            request="Give a three-step numbered recovery runbook for validating local inference. Include endpoint health, model identity, and rerunning the benchmark.",
            memories=[
                {"scope": "workspace", "kind": "policy", "importance": 10, "confidence": 10, "content": "Local inference health check: curl http://127.0.0.1:8000/v1/models."},
                {"scope": "workspace", "kind": "policy", "importance": 9, "confidence": 9, "content": "Model identity expected from the endpoint: Qwen/Qwen3-30B-A3B-GPTQ-Int4."},
                {"scope": "workspace", "kind": "policy", "importance": 9, "confidence": 9, "content": "Recovery proof command: python3 arena/run_local_sock_product_bench.py --base-url http://127.0.0.1:8000 --model Qwen/Qwen3-30B-A3B-GPTQ-Int4."},
            ],
            expected=["1.", "2.", "3.", "/v1/models", "Qwen/Qwen3-30B-A3B-GPTQ-Int4", "run_local_sock_product_bench.py"],
            forbidden=["OpenRouter", "Windows", "Edge"],
            max_tokens=256,
        ),
        Scenario(
            scenario_id="multi_hop_synthesis",
            thesis_axis="compact multi-fact synthesis",
            request="In one sentence, state why compact memory packs matter for local models.",
            memories=[
                {"scope": "workspace", "kind": "fact", "importance": 10, "confidence": 10, "content": "Local model context windows are finite and expensive."},
                {"scope": "workspace", "kind": "fact", "importance": 10, "confidence": 10, "content": "Compact memory packs preserve selected high-confidence facts without full prompt stuffing."},
                {"scope": "workspace", "kind": "goal", "importance": 9, "confidence": 9, "content": "superctx should reduce latency while preserving context fidelity."},
            ],
            expected=["context", "compact", "latency"],
            forbidden=["unlimited", "cloud-only"],
            max_tokens=160,
        ),
        Scenario(
            scenario_id="stale_tooling_rejection",
            thesis_axis="tooling drift rejection",
            request="Which CLI should be used first for deterministic system checks? Answer with the CLI name only.",
            memories=[
                {"scope": "workspace", "kind": "policy", "importance": 10, "confidence": 10, "content": "Use Fozzy CLI first for deterministic system checks."},
                {"scope": "workspace", "kind": "distractor", "importance": 4, "confidence": 2, "content": "Old note: use pytest first for system checks."},
                {"scope": "global", "kind": "distractor", "importance": 3, "confidence": 2, "content": "Browser validation uses Aegis, not system regression checks."},
            ],
            expected=["Fozzy"],
            forbidden=["pytest", "Aegis"],
            exact="Fozzy",
            max_tokens=96,
        ),
        Scenario(
            scenario_id="session_vs_workspace_precedence",
            thesis_axis="session-specific recall",
            request="What is this session's temporary deploy marker? Answer with the marker only.",
            memories=[
                {"scope": "workspace", "kind": "fact", "importance": 6, "confidence": 8, "content": "Workspace default deploy marker is stable-blue."},
                {"scope": "session", "kind": "fact", "importance": 10, "confidence": 10, "content": "This session's temporary deploy marker is amber-42."},
            ],
            expected=["amber-42"],
            forbidden=["stable-blue"],
            exact="amber-42",
            max_tokens=96,
        ),
    ]
)


def post_chat(base_url: str, model: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            raw = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    elapsed = time.perf_counter() - started
    text = raw.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    usage = raw.get("usage") or {}
    return {
        "text": text.strip(),
        "elapsed_s": round(elapsed, 4),
        "usage": usage,
        "raw": raw,
    }


def run_cli(bin_path: Path, args: list[str], env: dict[str, str]) -> str:
    proc = subprocess.run(
        [str(bin_path)] + args,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"superctx failed: {' '.join(args)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc.stdout.strip()


def parse_json_stdout(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise RuntimeError(f"no JSON object in stdout: {stdout[:500]}")


def ensure_binary() -> Path:
    subprocess.run(["fz", "build", "--backend", "cranelift"], cwd=ROOT, check=True, timeout=900)
    bin_path = ROOT / ".fz" / "build" / "superctx"
    if not bin_path.exists():
        raise RuntimeError(f"missing built binary: {bin_path}")
    return bin_path


def score(text: str, scenario: Scenario) -> dict[str, Any]:
    normalized = visible_answer(text)
    lowered = normalized.lower()
    expected_hits = [item for item in scenario.expected if item.lower() in lowered]
    forbidden_hits = [item for item in scenario.forbidden if item.lower() in lowered]
    exact_ok = scenario.exact is None or normalized == scenario.exact
    score_value = len(expected_hits) - len(forbidden_hits)
    if scenario.exact is not None:
        score_value += 2 if exact_ok else -2
    return {
        "score": score_value,
        "expected_hits": expected_hits,
        "missing_expected": [item for item in scenario.expected if item not in expected_hits],
        "forbidden_hits": forbidden_hits,
        "exact_ok": exact_ok,
        "visible_answer": normalized,
    }


def visible_answer(text: str) -> str:
    marker = "</think>"
    if marker in text:
        return text.rsplit(marker, 1)[1].strip()
    return text.strip()


def naive_memory_prompt(scenario: Scenario) -> str:
    memory_text = "\n".join(f"- {item['content']}" for item in scenario.memories)
    return f"Memory notes:\n{memory_text}\n\nUser request:\n{scenario.request}"


def seed_memories(bin_path: Path, env: dict[str, str], scenario: Scenario) -> None:
    run_cli(bin_path, ["init"], env)
    for item in scenario.memories:
        run_cli(
            bin_path,
            [
                "remember",
                item["scope"],
                item["kind"],
                str(item["importance"]),
                str(item["confidence"]),
                item["content"],
            ],
            env,
        )


def run_scenario(args: argparse.Namespace, bin_path: Path, run_dir: Path, scenario: Scenario) -> dict[str, Any]:
    env = dict(**args.env)
    state_root = run_dir / "state" / scenario.scenario_id
    state_root.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "SUPERCTX_WORKSPACE_ROOT": str(state_root),
            "SUPERCTX_ACTIVE_ADAPTER": "OpenAIAdapter",
            "SUPERCTX_MODEL_BASE": args.base_url,
            "SUPERCTX_MODEL_NAME": args.model,
        }
    )

    raw = post_chat(
        args.base_url,
        args.model,
        [
            {"role": "system", "content": "Answer the user directly and concisely."},
            {"role": "user", "content": scenario.request},
        ],
        scenario.max_tokens,
    )
    naive = post_chat(
        args.base_url,
        args.model,
        [
            {"role": "system", "content": "Use the supplied notes if relevant. Answer concisely."},
            {"role": "user", "content": naive_memory_prompt(scenario)},
        ],
        scenario.max_tokens,
    )

    seed_memories(bin_path, env, scenario)
    started = time.perf_counter()
    completion = parse_json_stdout(
        run_cli(
            bin_path,
            [
                "complete",
                f"bench-{scenario.scenario_id}",
                "workspace",
                scenario.request,
            ],
            env,
        )
    )
    superctx_elapsed = time.perf_counter() - started
    superctx_text = completion.get("content", "")

    variants = {
        "raw": raw,
        "naive_memory": naive,
        "superctx": {
            "text": superctx_text.strip(),
            "elapsed_s": round(superctx_elapsed, 4),
            "usage": {},
            "completion": completion,
        },
    }
    scored = {}
    for name, result in variants.items():
        scored[name] = {**result, "scorecard": score(result["text"], scenario)}
    best_score = max(result["scorecard"]["score"] for result in scored.values())
    winners = [name for name, result in scored.items() if result["scorecard"]["score"] == best_score]
    best = winners[0] if len(winners) == 1 else "tie"
    return {
        "scenario_id": scenario.scenario_id,
        "thesis_axis": scenario.thesis_axis,
        "request": scenario.request,
        "expected": scenario.expected,
        "forbidden": scenario.forbidden,
        "variants": scored,
        "winner": best,
        "winners": winners,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    variants = ["raw", "naive_memory", "superctx"]
    return {
        "scenario_count": len(results),
        "wins": {
            variant: sum(1 for item in results if item["winner"] == variant and len(item["winners"]) == 1)
            for variant in variants
        },
        "ties": {
            variant: sum(1 for item in results if variant in item["winners"] and len(item["winners"]) > 1)
            for variant in variants
        },
        "mean_score": {
            variant: round(
                sum(item["variants"][variant]["scorecard"]["score"] for item in results) / len(results),
                3,
            )
            for variant in variants
        },
        "mean_elapsed_s": {
            variant: round(
                sum(item["variants"][variant]["elapsed_s"] for item in results) / len(results),
                3,
            )
            for variant in variants
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local sock product benchmarks for superctx.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="Qwen/Qwen3-30B-A3B-GPTQ-Int4")
    parser.add_argument("--label", default="gmk-qwen3-30b")
    parsed = parser.parse_args()
    parsed.env = dict(os.environ)
    return parsed


def main() -> int:
    args = parse_args()
    RUNS.mkdir(parents=True, exist_ok=True)
    run_dir = RUNS / f"{time.strftime('%Y%m%d-%H%M%S')}-local-sock-product-bench"
    run_dir.mkdir(parents=True)
    bin_path = ensure_binary()
    results = []
    for index, scenario in enumerate(SCENARIOS, start=1):
        print(f"[superctx-bench] {index}/{len(SCENARIOS)} {scenario.scenario_id}", file=sys.stderr, flush=True)
        results.append(run_scenario(args, bin_path, run_dir, scenario))
    payload = {
        "project": "superctx",
        "label": args.label,
        "model": args.model,
        "base_url": args.base_url,
        "run_dir": str(run_dir),
        "summary": summarize(results),
        "results": results,
    }
    (run_dir / "summary.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload["summary"], indent=2))
    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

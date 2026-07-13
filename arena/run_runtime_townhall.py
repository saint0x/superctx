#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

import eval_model as base


ROOT = Path("/Users/deepsaint/Desktop/superctx")
RUNS = ROOT / "arena" / "runs"
DEFAULT_MODELS = [
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "qwen/qwen3.5-9b",
    "mistralai/mistral-nemo",
    "google/gemma-4-26b-a4b-it:free",
]
SLEEP_SECS = float(os.environ.get("SUPERCTX_TOWNHALL_SLEEP_SECS", "6"))


ROUNDS = [
    {
        "id": "quorum_math",
        "mode": "exact",
        "prompt": (
            "War room round 1. Use the calculator tool for 183 * 27 and answer with the number only. "
            "This exact number is the checkpoint code for the incident bridge."
        ),
        "allowed_tools": ["calc"],
        "must_use": ["calc"],
        "exact_output": "4941",
        "expects": ["4941"],
    },
    {
        "id": "runtime_grounding",
        "mode": "local_inspect",
        "prompt": (
            "War room round 2. Inspect /Users/deepsaint/Desktop/superctx and answer in 2 sentences max. "
            "Read the local docs or source, then name the designed persistent brain database path and one exact "
            "validator-related repo path. Use only local file tools and cite the path strings directly."
        ),
        "allowed_tools": ["list_dir", "read_file", "grep_text"],
        "must_use": ["list_dir", "read_file"],
        "expects": [".brain/brain.db", "/Users/deepsaint/Desktop/superctx/src/services/validator.fzy"],
    },
    {
        "id": "incident_command",
        "mode": "engineering",
        "prompt": (
            "War room round 3. A Raft-like write service is duplicating client writes after leader failover "
            "during a GPU-backed rollout. Give a 5-line incident command plan. It must include the exact "
            "brain database path already identified, one idempotency or commit-semantics remediation, and "
            "one exact Fozzy verification command."
        ),
        "allowed_tools": [],
        "expects": [".brain/brain.db", "idempot", "fz trace verify"],
    },
    {
        "id": "state_recall",
        "mode": "exact",
        "prompt": (
            "War room round 4. What exact persistent brain database path did you already identify earlier? "
            "Answer with the path only."
        ),
        "allowed_tools": [],
        "exact_output": ".brain/brain.db",
        "expects": [".brain/brain.db"],
    },
    {
        "id": "grounding_policy",
        "mode": "engineering",
        "prompt": (
            "War room round 5. For this incident, should you browse the web before finishing the first local "
            "repo diagnosis? Answer yes or no, then one sentence grounded in local-runtime practice."
        ),
        "allowed_tools": [],
        "expects": ["no", "local"],
    },
]


def parse_models(argv: list[str]) -> list[str]:
    if argv:
        return argv
    env_models = os.environ.get("SUPERCTX_TOWNHALL_MODELS", "")
    if env_models.strip():
        return [item.strip() for item in env_models.split(",") if item.strip()]
    return DEFAULT_MODELS


def usage_total(log: list[dict]) -> dict:
    return {
        "input_tokens": sum(item.get("input_tokens", 0) for item in log),
        "output_tokens": sum(item.get("output_tokens", 0) for item in log),
        "total_tokens": sum(item.get("total_tokens", 0) for item in log),
    }


def call_openrouter(messages: list[dict], tools: list[dict]) -> tuple[dict, dict]:
    payload = {"model": base.OPENROUTER_MODEL, "messages": messages, "temperature": 0.1}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    response = base.post_json_with_retry(
        f"{base.OPENROUTER_BASE}/chat/completions",
        payload,
        timeout=120,
        headers={
            "Authorization": f"Bearer {base.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://superctx.local",
            "X-Title": "superctx-townhall",
        },
        retries=base.OPENROUTER_MAX_RETRIES,
    )
    return response, base.usage_from_openrouter(response)


def execute_round(transcript: list[dict], round_def: dict) -> dict:
    messages = list(transcript)
    messages.append({"role": "system", "content": base.policy_message(round_def)})
    messages.append({"role": "user", "content": round_def["prompt"]})
    tools = base.build_tools(round_def)
    used_tools = []
    tool_results = []
    usage_log = []
    final_text = ""

    for _ in range(4):
        response, usage = call_openrouter(messages, tools)
        usage_log.append(usage)
        choice = response["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        if tool_calls:
            for call in tool_calls:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"] or "{}")
                if name not in round_def.get("allowed_tools", []):
                    result = {"status": "error", "message": f"tool_not_allowed: {name}", "authoritative": True}
                else:
                    result = base.call_tool(name, args)
                used_tools.append(name)
                tool_results.append({"name": name, "arguments": args, "result": result})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": name,
                        "content": json.dumps(result),
                    }
                )
            continue
        final_text = (choice.get("content") or "").strip()
        break

    exact_required = round_def.get("exact_output") or base.authoritative_requirement(round_def, tool_results)
    exact_ok = exact_required is None or final_text == exact_required
    lowered = final_text.lower()
    expected_hits = [needle for needle in round_def.get("expects", []) if needle.lower() in lowered]
    must_use = round_def.get("must_use", [])
    tool_ok = all(tool in used_tools for tool in must_use)
    expect_ok = len(expected_hits) == len(round_def.get("expects", []))
    status = "pass" if tool_ok and exact_ok and expect_ok else "review"
    return {
        "round": round_def["id"],
        "mode": round_def["mode"],
        "status": status,
        "used_tools": used_tools,
        "tool_results": tool_results,
        "expected_hits": expected_hits,
        "missing_expectations": [x for x in round_def.get("expects", []) if x not in expected_hits],
        "exact_required": exact_required,
        "exact_ok": exact_ok,
        "final_text": final_text,
        "usage_log": usage_log,
        "token_usage": usage_total(usage_log),
        "messages": messages,
    }


def run_model(model: str) -> dict:
    base.OPENROUTER_MODEL = model
    transcript = [{"role": "system", "content": base.SYSTEM_PROMPT}]
    rounds = []
    for round_def in ROUNDS:
        result = execute_round(transcript, round_def)
        rounds.append(result)
        transcript = result["messages"]
    passes = sum(1 for item in rounds if item["status"] == "pass")
    aggregate = {
        "input_tokens": sum(item["token_usage"]["input_tokens"] for item in rounds),
        "output_tokens": sum(item["token_usage"]["output_tokens"] for item in rounds),
        "total_tokens": sum(item["token_usage"]["total_tokens"] for item in rounds),
    }
    return {
        "provider": "openrouter",
        "model": model,
        "passed": passes,
        "total": len(rounds),
        "token_usage": aggregate,
        "rounds": rounds,
    }


def main() -> int:
    if not base.OPENROUTER_API_KEY:
        raise SystemExit("missing OPENROUTER_API_KEY")
    RUNS.mkdir(parents=True, exist_ok=True)
    models = parse_models(sys.argv[1:])
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = RUNS / f"{ts}-townhall"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, model in enumerate(models):
        if index:
            time.sleep(SLEEP_SECS)
        print(f"running {model}", flush=True)
        started = time.time()
        try:
            result = run_model(model)
            result["duration_secs"] = round(time.time() - started, 2)
        except Exception as exc:
            result = {
                "provider": "openrouter",
                "model": model,
                "passed": 0,
                "total": len(ROUNDS),
                "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "rounds": [],
                "duration_secs": round(time.time() - started, 2),
                "error": str(exc),
            }
        slug = model.replace("/", "__").replace(":", "__")
        (out_dir / f"{slug}.json").write_text(json.dumps(result, indent=2))
        results.append(result)
        print(
            json.dumps(
                {
                    "model": result["model"],
                    "passed": result.get("passed", 0),
                    "total": result.get("total", len(ROUNDS)),
                    "token_usage": result.get("token_usage", {}),
                    "duration_secs": result.get("duration_secs"),
                    "error": result.get("error"),
                },
                indent=2,
            ),
            flush=True,
        )

    leaderboard = sorted(
        results,
        key=lambda item: (item.get("passed", 0), -item.get("token_usage", {}).get("total_tokens", 0)),
        reverse=True,
    )
    payload = {"models": models, "results": results, "leaderboard": leaderboard}
    (out_dir / "townhall_summary.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"townhall_dir": str(out_dir), "leaderboard": leaderboard}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

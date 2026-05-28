#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path("/Users/deepsaint/Desktop/superctx")
ARENA = ROOT / "arena"
RUNS = ARENA / "runs"
MODEL_BASE = os.environ.get("SUPERCTX_MODEL_BASE", "http://127.0.0.1:1234")
MODEL_NAME = os.environ.get("SUPERCTX_MODEL_NAME", "liquid/lfm2.5-1.2b")
AEGIS_BASE = os.environ.get("SUPERCTX_AEGIS_BASE", "http://127.0.0.1:7878")
SYSTEM_PROMPT = (ROOT / "config" / "fzl_system_prompt.md").read_text()


def ensure_dirs():
    RUNS.mkdir(parents=True, exist_ok=True)


def post_json(url: str, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_dir(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"status": "error", "message": f"path_not_found: {path}"}
    entries = []
    for child in sorted(p.iterdir()):
        entries.append(
            {
                "name": child.name,
                "kind": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size,
            }
        )
    return {"status": "ok", "path": str(p), "entries": entries[:200]}


def read_file(path: str, max_chars: int = 6000) -> dict:
    p = Path(path)
    if not p.exists():
        return {"status": "error", "message": f"path_not_found: {path}"}
    text = p.read_text(errors="replace")
    return {
        "status": "ok",
        "path": str(p),
        "chars": len(text),
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


def grep_text(pattern: str, path: str) -> dict:
    try:
        proc = subprocess.run(
            ["rg", "-n", pattern, path],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "status": "ok" if proc.returncode in (0, 1) else "error",
            "stdout": proc.stdout[:8000],
            "stderr": proc.stderr[:2000],
            "returncode": proc.returncode,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def calc(expr: str) -> dict:
    safe = expr.replace(" ", "")
    allowed = set("0123456789+-*/().%")
    if any(ch not in allowed for ch in safe):
        return {"status": "error", "message": "unsupported_expression", "authoritative": False}
    try:
        value = eval(safe, {"__builtins__": {}}, {})
    except Exception as exc:
        return {"status": "error", "message": str(exc), "authoritative": False}
    return {"status": "ok", "expr": expr, "value": value, "authoritative": True, "result_kind": "exact_value"}


def aegis_health() -> dict:
    payload = get_json(f"{AEGIS_BASE}/healthz", timeout=15)
    payload["authoritative"] = True
    payload["result_kind"] = "health"
    return payload


def aegis_manifest() -> dict:
    try:
        payload = get_json(f"{AEGIS_BASE}/manifest", timeout=15)
        return {"status": "ok", "manifest": payload, "authoritative": True, "result_kind": "route_manifest"}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "authoritative": False}


def aegis_navigate(url: str) -> dict:
    payload = post_json(f"{AEGIS_BASE}/navigate", {"url": url}, timeout=45)
    if isinstance(payload, dict):
        payload["authoritative"] = True
        payload["result_kind"] = "navigation"
        return payload
    return {"status": "ok", "payload": payload, "authoritative": True, "result_kind": "navigation"}


def aegis_execute_eval(code: str) -> dict:
    payload = post_json(f"{AEGIS_BASE}/execute", {"commands": [{"type": "eval", "code": code}]}, timeout=45)
    return {"status": "ok", "payload": payload, "authoritative": True, "result_kind": "dom_extract"}


def aegis_dom() -> dict:
    payload = get_json(f"{AEGIS_BASE}/dom", timeout=30)
    return {"status": "ok", "dom": payload, "authoritative": True, "result_kind": "dom_snapshot"}


ALL_TOOLS = {
    "list_dir": {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories under a local path.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    "read_file": {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a local text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    "grep_text": {
        "type": "function",
        "function": {
            "name": "grep_text",
            "description": "Search local text content with ripgrep.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern", "path"],
            },
        },
    },
    "calc": {
        "type": "function",
        "function": {
            "name": "calc",
            "description": "Evaluate a small arithmetic expression. The returned value is authoritative.",
            "parameters": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        },
    },
    "aegis_health": {
        "type": "function",
        "function": {
            "name": "aegis_health",
            "description": "Check that the Aegis browser runtime is healthy.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "aegis_manifest": {
        "type": "function",
        "function": {
            "name": "aegis_manifest",
            "description": "Return the Aegis route manifest when available. Prefer this for exact endpoint discovery.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "aegis_navigate": {
        "type": "function",
        "function": {
            "name": "aegis_navigate",
            "description": "Navigate the Aegis browser to a URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    "aegis_execute_eval": {
        "type": "function",
        "function": {
            "name": "aegis_execute_eval",
            "description": "Execute DOM extraction JavaScript in the current Aegis page and return the exact result.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
    "aegis_dom": {
        "type": "function",
        "function": {
            "name": "aegis_dom",
            "description": "Return a DOM snapshot from the current Aegis page.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
}


def call_tool(name: str, arguments: dict) -> dict:
    if name == "list_dir":
        return list_dir(arguments["path"])
    if name == "read_file":
        return read_file(arguments["path"], int(arguments.get("max_chars", 6000)))
    if name == "grep_text":
        return grep_text(arguments["pattern"], arguments["path"])
    if name == "calc":
        return calc(arguments["expr"])
    if name == "aegis_health":
        return aegis_health()
    if name == "aegis_manifest":
        return aegis_manifest()
    if name == "aegis_navigate":
        return aegis_navigate(arguments["url"])
    if name == "aegis_execute_eval":
        return aegis_execute_eval(arguments["code"])
    if name == "aegis_dom":
        return aegis_dom()
    return {"status": "error", "message": f"unknown_tool: {name}", "authoritative": False}


TASKS = [
    {
        "id": "calc_tool",
        "mode": "exact",
        "prompt": "Use the calculator tool and give the final numeric answer for 183 * 27.",
        "allowed_tools": ["calc"],
        "must_use": ["calc"],
        "exact_output": "4941",
    },
    {
        "id": "fzl_manual",
        "mode": "engineering",
        "prompt": "In FZL, where should a repository-specific build command live, and which brain tool should store it durably? Answer briefly and stay grounded in the system prompt.",
        "allowed_tools": [],
        "expects": ["workspace", "brain.remember"],
    },
    {
        "id": "repo_inspect",
        "mode": "local_inspect",
        "prompt": "Inspect /Users/deepsaint/Desktop/superctx and name two concrete limitations that still keep superctx from being full-spec production. Use only local file tools and include file references.",
        "allowed_tools": ["list_dir", "read_file", "grep_text"],
        "must_use": ["list_dir", "read_file"],
        "expects": ["SQLite", "adapter", "/Users/deepsaint/Desktop/superctx/src/services", "/Users/deepsaint/Desktop/superctx/src/runtime"],
    },
    {
        "id": "coding_agent_local",
        "mode": "local_inspect",
        "prompt": "You are acting as a coding agent on /Users/deepsaint/Desktop/superctx. Identify one concrete architectural weakness in the current implementation and one targeted next step to improve it. Use only local file tools and cite exact repo paths.",
        "allowed_tools": ["list_dir", "read_file", "grep_text"],
        "must_use": ["list_dir", "read_file"],
        "expects": ["superctx", "/Users/deepsaint/Desktop/superctx/src/", "runtime", "adapter"],
    },
    {
        "id": "distributed_systems",
        "mode": "engineering",
        "prompt": "You are reviewing a Raft-like service where duplicate client writes appear after leader failover. Give the most likely causes and a remediation checklist. Be concrete and systems-focused.",
        "allowed_tools": [],
        "expects": ["idempot", "term", "log", "commit", "retry"],
    },
    {
        "id": "gpu_programming",
        "mode": "engineering",
        "prompt": "A CUDA kernel is memory-bandwidth bound and suffers from warp divergence in boundary checks. Give a concise optimization plan an experienced GPU programmer would use.",
        "allowed_tools": [],
        "expects": ["coales", "occup", "shared", "diverg", "profile"],
    },
    {
        "id": "live_search",
        "mode": "live_search",
        "prompt": "Use the exact Aegis route surfaces to find what endpoints Aegis exposes for navigation and DOM inspection, then answer with the exact route paths only.",
        "allowed_tools": ["aegis_health", "aegis_manifest", "aegis_navigate", "aegis_execute_eval", "aegis_dom"],
        "must_use": ["aegis_health"],
        "expects": ["/navigate", "/dom", "/events"],
    },
]


def policy_message(task: dict) -> str:
    if task["mode"] == "exact":
        return (
            "Task mode: exact.\n"
            "Use only the allowed tools.\n"
            "If an authoritative tool returns a value, your final answer must equal that value exactly.\n"
            "Do not add explanation unless asked."
        )
    if task["mode"] == "local_inspect":
        return (
            "Task mode: local_inspect.\n"
            "Use only the allowed local tools.\n"
            "Do not use freshness-seeking behavior.\n"
            "Every concrete claim must be grounded in local evidence and cite exact local paths."
        )
    if task["mode"] == "live_search":
        return (
            "Task mode: live_search.\n"
            "Prefer exact structured extraction tools over broad summaries.\n"
            "Return only the exact route paths requested.\n"
            "Do not invent routes."
        )
    return (
        "Task mode: engineering.\n"
        "Stay concise and grounded.\n"
        "Separate observed facts from inference when evidence is limited."
    )


def build_tools(task: dict) -> list:
    return [ALL_TOOLS[name] for name in task.get("allowed_tools", [])]


def authoritative_requirement(task: dict, tool_results: list) -> str | None:
    if task["mode"] != "exact":
        return None
    for item in reversed(tool_results):
        result = item["result"]
        if result.get("authoritative") and "value" in result:
            return str(result["value"])
    return None


def run_task(task: dict) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": policy_message(task)},
        {
            "role": "user",
            "content": task["prompt"],
        },
    ]
    tools = build_tools(task)
    used_tools = []
    tool_results = []
    final_text = ""

    for _ in range(4):
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.1,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        response = post_json(f"{MODEL_BASE}/v1/chat/completions", payload, timeout=90)
        choice = response["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        if tool_calls:
            for call in tool_calls:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"] or "{}")
                if task.get("allowed_tools") is not None and name not in task.get("allowed_tools", []):
                    result = {"status": "error", "message": f"tool_not_allowed: {name}", "authoritative": True}
                else:
                    result = call_tool(name, args)
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

    lowered = final_text.lower()
    expected_hits = [needle for needle in task.get("expects", []) if needle.lower() in lowered]
    must_use = task.get("must_use", [])
    tool_ok = all(tool in used_tools for tool in must_use)
    exact_required = authoritative_requirement(task, tool_results)
    exact_ok = exact_required is None or final_text == exact_required
    expect_ok = len(expected_hits) == len(task.get("expects", []))
    status = "pass" if tool_ok and exact_ok and expect_ok else "review"
    return {
        "task": task["id"],
        "mode": task["mode"],
        "status": status,
        "used_tools": used_tools,
        "tool_results": tool_results,
        "expected_hits": expected_hits,
        "missing_expectations": [x for x in task.get("expects", []) if x not in expected_hits],
        "exact_required": exact_required,
        "exact_ok": exact_ok,
        "final_text": final_text,
        "messages": messages,
    }


def main() -> int:
    ensure_dirs()
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = RUNS / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    requested = set(sys.argv[1:])
    selected = [task for task in TASKS if not requested or task["id"] in requested]
    summary = []
    for task in selected:
        try:
            result = run_task(task)
        except Exception as exc:
            result = {
                "task": task["id"],
                "mode": task["mode"],
                "status": "error",
                "used_tools": [],
                "tool_results": [],
                "expected_hits": [],
                "missing_expectations": task.get("expects", []),
                "exact_required": None,
                "exact_ok": False,
                "final_text": "",
                "error": str(exc),
                "messages": [],
            }
        summary.append(result)
        (out_dir / f"{task['id']}.json").write_text(json.dumps(result, indent=2))
        print(f"{task['id']}: {result['status']}")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    passed = sum(1 for item in summary if item["status"] == "pass")
    print(json.dumps({"run_dir": str(out_dir), "passed": passed, "total": len(summary)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

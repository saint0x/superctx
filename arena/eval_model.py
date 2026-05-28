#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
import subprocess


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
        return {"status": "error", "message": "unsupported_expression"}
    try:
        value = eval(safe, {"__builtins__": {}}, {})
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
    return {"status": "ok", "expr": expr, "value": value}


def aegis_health() -> dict:
    return get_json(f"{AEGIS_BASE}/healthz", timeout=15)


def aegis_navigate(url: str) -> dict:
    return post_json(f"{AEGIS_BASE}/navigate", {"url": url}, timeout=45)


def aegis_execute(commands: list) -> dict:
    return post_json(f"{AEGIS_BASE}/execute", {"commands": commands}, timeout=45)


def aegis_search(query: str) -> dict:
    target = "https://duckduckgo.com/?q=" + urllib.parse.quote(query)
    nav = aegis_navigate(target)
    time.sleep(2)
    extract = aegis_execute(
        [{"type": "eval", "code": "document.body ? document.body.innerText.slice(0, 5000) : ''"}]
    )
    return {"status": "ok", "query": query, "navigate": nav, "extract": extract}


TOOLS = [
    {
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
    {
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
    {
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
    {
        "type": "function",
        "function": {
            "name": "calc",
            "description": "Evaluate a small arithmetic expression.",
            "parameters": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aegis_health",
            "description": "Check that the Aegis browser runtime is healthy.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aegis_search",
            "description": "Search the live web through Aegis and return extracted visible text.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


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
    if name == "aegis_search":
        return aegis_search(arguments["query"])
    return {"status": "error", "message": f"unknown_tool: {name}"}


TASKS = [
    {
        "id": "calc_tool",
        "prompt": "Use the calculator tool and give the final numeric answer for 183 * 27.",
        "expects": ["4941"],
        "must_use": ["calc"],
    },
    {
        "id": "fzl_manual",
        "prompt": "In FZL, where should a repository-specific build command live, and which brain tool should store it durably? Answer briefly.",
        "expects": ["workspace", "brain.remember"],
    },
    {
        "id": "repo_inspect",
        "prompt": "Inspect /Users/deepsaint/Desktop/superctx and name two concrete limitations that still keep superctx from being full-spec production. Use only local file tools unless you truly need freshness, and include file references when relevant.",
        "expects": ["SQLite", "adapter", "src/services", "src/runtime"],
        "must_use": ["list_dir", "read_file"],
    },
    {
        "id": "coding_agent_local",
        "prompt": "You are acting as a coding agent on /Users/deepsaint/Desktop/superctx. Identify one concrete architectural weakness in the current implementation and one targeted next step to improve it. Use local file tools and cite exact repo paths.",
        "expects": ["superctx", "src/", "path", "runtime"],
        "must_use": ["list_dir", "read_file"],
    },
    {
        "id": "distributed_systems",
        "prompt": "You are reviewing a Raft-like service where duplicate client writes appear after leader failover. Give the most likely causes and a remediation checklist. Be concrete and systems-focused.",
        "expects": ["idempot", "term", "log", "commit", "retry"],
    },
    {
        "id": "gpu_programming",
        "prompt": "A CUDA kernel is memory-bandwidth bound and suffers from warp divergence in boundary checks. Give a concise optimization plan an experienced GPU programmer would use.",
        "expects": ["coales", "occup", "shared", "diverg", "profile"],
    },
    {
        "id": "live_search",
        "prompt": "Use live web search via Aegis to find what endpoints Aegis exposes for navigation and DOM inspection, then answer with the exact route paths only.",
        "expects": ["/navigate", "/dom", "/events"],
        "must_use": ["aegis_search"],
    },
]


def run_task(task: dict) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                task["prompt"]
                + "\n\nYou may use tools. Be accurate, explicit about uncertainty, and cite concrete local paths or route names when possible."
            ),
        },
    ]
    used_tools = []
    final_text = ""

    for _ in range(8):
        response = post_json(
            f"{MODEL_BASE}/v1/chat/completions",
            {
                "model": MODEL_NAME,
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.2,
            },
            timeout=90,
        )
        choice = response["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        if tool_calls:
            for call in tool_calls:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"] or "{}")
                used_tools.append(name)
                result = call_tool(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": name,
                        "content": json.dumps(result),
                    }
                )
            continue
        final_text = choice.get("content", "")
        break

    lowered = final_text.lower()
    expected_hits = [needle for needle in task.get("expects", []) if needle.lower() in lowered]
    must_use = task.get("must_use", [])
    tool_ok = all(tool in used_tools for tool in must_use)
    status = "pass" if len(expected_hits) == len(task.get("expects", [])) and tool_ok else "review"
    return {
        "task": task["id"],
        "status": status,
        "used_tools": used_tools,
        "expected_hits": expected_hits,
        "missing_expectations": [x for x in task.get("expects", []) if x not in expected_hits],
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
                "status": "error",
                "used_tools": [],
                "expected_hits": [],
                "missing_expectations": task.get("expects", []),
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

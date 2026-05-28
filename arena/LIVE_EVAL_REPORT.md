# Superctx Live Model Evaluation

Date: 2026-05-28

Model under test:
- endpoint: `http://127.0.0.1:1234/v1/chat/completions`
- model: `liquid/lfm2.5-1.2b`

Tool/runtime environment:
- FZL system prompt source: [config/fzl_system_prompt.md](../config/fzl_system_prompt.md)
- arena harness: [arena/eval_model.py](./eval_model.py)
- Aegis control plane: `http://127.0.0.1:7878`
- Aegis health at end of run: `ready`, `command_ready=true`, `bridge_healthy=true`

## Summary

The `superctx` runtime itself is in good shape for a scoped JSON-first v0.1 evaluation flow.

The local model is not yet production-ready as a high-trust engineering agent under this setup.

The dominant failure mode is not lack of tool access. It is post-tool mis-grounding:
- it calls tools, receives usable results, and then answers incorrectly anyway
- it overuses live search when the answer is already available locally or directly in the prompt
- it latches onto irrelevant DuckDuckGo page text and turns that into fabricated engineering conclusions
- it does not reliably obey “use local file tools only unless freshness matters”

## Notable Failures

### 1. Arithmetic tool grounding failure

Artifact:
- local artifact: `arena/runs/20260528-181504/calc_tool.json`

Observed behavior:
- model called `calc`
- tool returned `4941`
- model answered `5241`

Meaning:
- the model cannot yet be trusted to faithfully copy or respect tool outputs, even for a trivial exact-answer task

### 2. FZL manual comprehension failure

Artifacts:
- local artifacts:
  - `arena/runs/20260528-181504/fzl_manual.json`
  - `arena/runs/20260528-181618/fzl_manual.json`

Observed behavior:
- instead of answering from the system prompt, it searched the web
- it then answered that the build command “lives in the DuckDuckGo browser”

Meaning:
- the prompt did not anchor the model strongly enough
- the model does not reliably distinguish internal operating-manual knowledge from freshness-sensitive knowledge

### 3. Local coding-agent inspection failure

Artifacts:
- local artifacts:
  - `arena/runs/20260528-181730/repo_inspect.json`
  - `arena/runs/20260528-181730/coding_agent_local.json`

Observed behavior:
- even when given the absolute repo path, it failed to inspect the implementation properly
- it sometimes searched for `superctx full-spec production limitations`
- it fabricated privacy-policy and cross-platform claims from DuckDuckGo chrome text
- in the more local-only task, it fixated on `SPEC.md` wording instead of the actual implementation under `src/`

Meaning:
- as a coding agent, it is not yet disciplined enough to stay grounded in the codebase
- file-tool access alone is not sufficient to make this model act like a strong repo analyst

### 4. Distributed systems reasoning failure

Artifact:
- local artifact: `arena/runs/20260528-181618/distributed_systems.json`

Observed behavior:
- it searched the web for a generic Raft issue
- it introduced irrelevant ideas like browser extensions affecting duplicate writes
- it missed important operator concepts like client request idempotency and retry dedupe

Meaning:
- this is not ready to be trusted as a distributed-systems engineer
- it can produce plausible structure, but not reliably correct systems diagnosis

### 5. GPU programming partial/unsafe confidence

Artifact:
- local artifact: `arena/runs/20260528-181618/gpu_programming.json`

Observed behavior:
- some correct concepts appeared: profiling, coalescing, shared memory, divergence
- it also hallucinated details like “NCU = NVIDIA Compute Uniform Interface”
- it suggested vague or low-signal steps such as “increase the number of threads per warp”
- it omitted a more concrete occupancy-focused line of attack

Meaning:
- this is the strongest area of the tested set, but still not trustworthy enough for expert GPU guidance without human review

### 6. Aegis route extraction failure

Artifact:
- local artifact: `arena/runs/20260528-181730/live_search.json`

Observed behavior:
- it used `aegis_search`
- returned an empty extracted page body
- then answered with the DuckDuckGo search URL instead of route paths like `/navigate`, `/dom`, `/events`

Meaning:
- the model does not recover well when search extraction is weak
- current `aegis_search` wrapper is usable for rough browsing but not yet robust enough for exact-route extraction tasks

## Production Readiness Assessment

### Superctx runtime

For the current scope, `superctx` is in decent shape:
- deterministic Fozzy validation is strong
- traces, replay, CI, host-backed passes, vendor state, and strict doctor all checked out
- the shared system prompt/manual now exists and is wired into the planner

But it is still a scoped v0.1:
- no real model adapter execution loop inside the Fzy runtime yet
- no SQLite-backed brain yet
- no first-class tool orchestration/validation loop between the model and runtime yet

### Local model as engineering agent

Not production-ready yet for:
- high-trust coding agent work
- distributed systems diagnosis
- GPU programming advice without review
- exact tool-grounded answers

## Recommended Next Steps

1. Add stricter tool-grounding middleware.
- Require the final answer to reference exact tool-returned values for exact-answer tasks.
- Consider answer post-checks for arithmetic and extraction tasks.

2. Split tools by intent and tighten policies.
- local repo tasks should not expose web search by default
- freshness-sensitive tasks can opt in to Aegis/web tools

3. Improve Aegis tool adapters.
- add `aegis_manifest`
- add `aegis_dom`
- add `aegis_execute_eval`
- avoid relying only on DuckDuckGo visible text for exact facts

4. Add hard evals with machine-checkable outputs.
- exact arithmetic
- exact route extraction
- exact file-path lookup
- exact implementation-gap identification from local source

5. Consider a stronger local model before trusting this workflow for expert engineering.

## Key Artifacts

- [config/fzl_system_prompt.md](/Users/deepsaint/Desktop/superctx/config/fzl_system_prompt.md)
- [arena/eval_model.py](./eval_model.py)
- local arena transcripts under `arena/runs/`

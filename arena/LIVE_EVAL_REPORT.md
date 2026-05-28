# Superctx Live Model Evaluation

Date: 2026-05-28

Model under test:
- endpoint: `http://127.0.0.1:1234/v1/chat/completions`
- model: `liquid/lfm2.5-1.2b`

Tool/runtime environment:
- FZL system prompt source: [config/fzl_system_prompt.md](/Users/deepsaint/Desktop/superctx/config/fzl_system_prompt.md)
- arena harness: [eval_model.py](/Users/deepsaint/Desktop/superctx/arena/eval_model.py)
- Aegis control plane: `http://127.0.0.1:7878`

## Summary

`superctx` is stronger after the protocol hardening pass.

The runtime now emits explicit task modes, answer contracts, grounding rules, allowed tool classes, and blocked tool classes into the compiled frame. The arena now enforces per-task tool allowlists, authoritative exact-result checks, and structured Aegis surfaces instead of loose search text.

The tested local model is still not production-ready as a high-trust engineering agent. The new protocol made failures cleaner and more diagnosable, but it did not materially improve the model’s accuracy.

Important attribution note:
- the runtime is not the primary failure source in these arena results
- the runtime is correctly constraining tool access, validating exact-answer behavior, tracing adapter I/O, and recording rejection/repair evidence
- the dominant failure source is model quality: the tested local model still ignores tool truth, misreads prompts, invents local paths, and makes bad retrieval decisions even under a stricter runtime contract
- in plain terms, the runtime is doing its job; the model still sucks

Latest strict arena run:
- run dir: [20260528-190636](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636)
- passed: `0/7`

## What Improved

1. Exact-answer tasks are now machine-checked.
- Artifact: [calc_tool.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/calc_tool.json)
- The runtime/harness correctly marks the answer as failed because the tool returned `4941` and the model still answered `5,091`.
- This is now a clean model failure, not an evaluator ambiguity.

2. Local-inspection tasks are now properly gated.
- Artifacts:
  - [repo_inspect.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/repo_inspect.json)
  - [coding_agent_local.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/coding_agent_local.json)
- Web-style drift is no longer the main problem.
- The model still invents bad local paths like `config.json` and `/repo/SPEC.md`, which is exactly the kind of grounding failure we want the protocol to expose.

3. Aegis evaluation is more structured.
- Artifact: [live_search.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/live_search.json)
- The previous harness crash is fixed.
- The model now fails because it navigates to a nonsense URL and never extracts the requested Aegis routes, not because the harness broke.

## Remaining Model Failures

### 1. Exact tool disobedience

Artifact:
- [calc_tool.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/calc_tool.json)

Observed behavior:
- model called `calc`
- tool returned `4941`
- model answered `5,091`

Meaning:
- this model cannot yet be trusted to copy authoritative tool outputs into the final answer

### 2. System-prompt/manual misunderstanding

Artifact:
- [fzl_manual.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/fzl_manual.json)

Observed behavior:
- it still says a repository-specific build command belongs in `session`
- the correct scoped answer is `workspace`, with durable storage via `brain.remember`

Meaning:
- prompt reading is still shallow and inconsistent

### 3. Local code inspection unreliability

Artifacts:
- [repo_inspect.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/repo_inspect.json)
- [coding_agent_local.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/coding_agent_local.json)

Observed behavior:
- it invents nonexistent local files
- it fails to follow the obvious repo structure after listing it
- it does not converge on `src/services` and `src/runtime` even when those paths are visible

Meaning:
- this is not yet dependable as a coding agent, even with local-only tool gating

### 4. Distributed systems reasoning still weak

Artifact:
- [distributed_systems.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/distributed_systems.json)

Observed behavior:
- the answer structure is better than random web drift, but it still does not reliably hit the full operator checklist we want

Meaning:
- it may sound plausible, but it is still not strong enough to trust as a distributed-systems engineer

### 5. GPU guidance is the best area, but still not expert-grade

Artifact:
- [gpu_programming.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/gpu_programming.json)

Observed behavior:
- it hits coalescing, shared memory, divergence, and profiling
- it still misses the expected occupancy line and includes weak suggestions

Meaning:
- this is the strongest domain tested, but still needs human review

### 6. Live route extraction still fails on judgment

Artifact:
- [live_search.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-190636/live_search.json)

Observed behavior:
- the model navigates to `https://example.com/route`
- then inspects that DOM instead of using the Aegis route surfaces meaningfully

Meaning:
- the runtime surface is better, but the model still makes poor tool-selection decisions

## Runtime Assessment

For a scoped v0.1 runtime, `superctx` is in good shape:
- stricter frame protocol is now present in [planner.fzy](/Users/deepsaint/Desktop/superctx/src/services/planner.fzy)
- richer tool semantics are now present in [adapters.fzy](/Users/deepsaint/Desktop/superctx/src/services/adapters.fzy)
- the frame schema now carries protocol policy in [types.fzy](/Users/deepsaint/Desktop/superctx/src/model/types.fzy)
- deterministic and strict Fozzy validation remain green

Current production posture:
- in-runtime answer validation is present, with rejection plus one repair attempt
- storage is under `.brain/brain.db` with SQLite FTS-backed retrieval and heuristic fallback
- real adapter execution exists for OpenAI-compatible, Ollama, MLX, and vLLM-style endpoints, plus a deterministic adapter for strict validation

Still worth improving:
- validation policy is still rule-based rather than task-complete or formally typed
- multi-provider coverage is broader now, but only the OpenAI-compatible path was live-exercised in this repo
- retrieval is materially better with FTS, but still not semantic in the embedding/reranker sense

## Validation Status

Passed after protocol changes:
- `fz check /Users/deepsaint/Desktop/superctx --json`
- `fz dx-check /Users/deepsaint/Desktop/superctx --strict --json`
- `fz doctor project /Users/deepsaint/Desktop/superctx --strict --json`
- `fz test /Users/deepsaint/Desktop/superctx/src/main.fzy --det --strict-verify --json`
- `fz test /Users/deepsaint/Desktop/superctx/src/main.fzy --det --strict-verify --host-backends --json`
- `fz run /Users/deepsaint/Desktop/superctx/src/main.fzy --det --record /Users/deepsaint/Desktop/superctx/artifacts/superctx.run.trace.fozzy --json`
- `fz doctor --deep --scenario /Users/deepsaint/Desktop/superctx/artifacts/superctx.trace.scenarios/all.fozzy.json --runs 5 --seed 4242 --json`
- `fz trace verify /Users/deepsaint/Desktop/superctx/artifacts/superctx.run.trace.fozzy --strict --json`
- `fz replay /Users/deepsaint/Desktop/superctx/artifacts/superctx.run.trace.fozzy --json`
- `fz ci /Users/deepsaint/Desktop/superctx/artifacts/superctx.run.trace.fozzy --json`
- `fz fuzz /Users/deepsaint/Desktop/superctx/artifacts/superctx.trace.scenarios/all.fozzy.json --json`

## Bottom Line

The protocol/runtime is materially better than before.

The local model is still the main limiting factor. The new runtime does not rescue a weak model, but it does constrain it better, surface failures earlier, and make it much easier to prove where the model is violating the contract.

If these same evals were run against a materially stronger model, the current evidence suggests the runtime would no longer be the main bottleneck.

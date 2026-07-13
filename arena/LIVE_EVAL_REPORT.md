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

Cloud baseline comparison:
- run dir: [20260528-191956](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956)
- provider: `anthropic`
- model: `claude-haiku-4-5-20251001`
- passed: `4/7`
- token usage:
  - input: `34,947`
  - output: `4,704`
  - total: `39,651`

Interpretation:
- the runtime quality is not the main explanation for the bad local-model result
- with the same arena, same task design, same prompt discipline, and stricter runtime contract, a cheap cloud baseline performs materially better
- the remaining misses on the cloud baseline are mostly evaluator-bar and grounding-discipline issues, not chaotic model collapse
- this reinforces the main attribution line for production: the runtime is doing its job; model quality is the dominant variable

## Haiku Baseline

To separate runtime failures from model failures, the same arena was rerun against the Anthropic Haiku model configured in `/Users/deepsaint/Desktop/fzyagent/.env`.

Run summary:
- artifact: [run_summary.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956/run_summary.json)
- provider: `anthropic`
- model: `claude-haiku-4-5-20251001`
- result: `4/7` pass
- total token I/O: `39,651`

Per-task outcome:
- pass: `calc_tool`
- pass: `fzl_manual`
- pass: `distributed_systems`
- pass: `gpu_programming`
- review: `repo_inspect`
- review: `coding_agent_local`
- review: `live_search`

What changed versus the weak local model:
- exact-answer obedience improved enough to pass the calculator task
- prompt/manual reading improved enough to answer workspace versus session correctly
- distributed-systems and GPU answers crossed the bar from plausible-but-weak to acceptable baseline quality
- local repo grounding improved a lot, but still fell short of the strict review threshold
- live search still showed over-inference when route discovery was incomplete

Representative artifacts:
- [calc_tool.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956/calc_tool.json)
- [distributed_systems.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956/distributed_systems.json)
- [gpu_programming.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956/gpu_programming.json)
- [repo_inspect.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956/repo_inspect.json)
- [coding_agent_local.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956/coding_agent_local.json)
- [live_search.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-191956/live_search.json)

## OpenRouter Sweeps

To widen the model search without jumping to expensive frontier models, `superctx` was run against live OpenRouter candidates in two passes:
- a broad free-model sweep to find rough capability ceilings
- a tighter cheap-tier sweep emphasizing smaller or lower-cost models that plausibly hover around Haiku quality

Model discovery note:
- the OpenRouter live API catalog at `https://openrouter.ai/api/v1/models` was used as the authoritative directory surface for model ids and pricing
- the local Aegis runtime was also checked and an Aegis-backed browse pass to `https://openrouter.ai/models` was attempted, but the runtime timed out on `navigate` / `dom` during this session
- because of that, Aegis was useful as an availability check but not as the primary model-directory extraction path here

### Broad Free Sweep

Sweep artifact:
- [openrouter_sweep.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-193100-openrouter-sweep/openrouter_sweep.json)

Results:
- `openai/gpt-oss-120b:free`: `4/7`, `17,493` total tokens
- `z-ai/glm-4.5-air:free`: `3/7`, `18,633` total tokens
- `poolside/laguna-xs.2:free`: `3/7`, `25,776` total tokens
- `poolside/laguna-m.1:free`: `2/7`, `22,657` total tokens
- `nvidia/nemotron-3-super:free`: invalid model id in the first sweep configuration, so this was not a meaningful quality result

Interpretation:
- `gpt-oss-120b:free` tied the Haiku cloud baseline on pass count
- `glm-4.5-air:free` and `laguna-xs.2:free` were respectable but clearly below the top free result
- `laguna-m.1:free` underperformed relative to its positioning
- the first Nemotron miss was a directory/config mistake, not a model-capability failure

### Cheap-Tier Curated Sweep

Sweep artifact:
- [openrouter_sweep.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-200557-openrouter-sweep/openrouter_sweep.json)

This pass intentionally favored cheap or free models that looked closer to the Haiku quality band than to the top-end frontier band:
- `openai/gpt-oss-20b:free`
- `openai/gpt-oss-20b`
- `mistralai/mistral-nemo`
- `mistralai/mistral-small-24b-instruct-2501`
- `qwen/qwen3.5-9b`
- `google/gemma-3-12b-it`
- `amazon/nova-micro-v1`
- `nvidia/nemotron-3-nano-30b-a3b:free`

Leaderboard:
- `openai/gpt-oss-20b:free`: `4/7`, `21,072` total tokens, run: [20260528-200557](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-200557)
- `openai/gpt-oss-20b`: `4/7`, `23,608` total tokens, run: [20260528-200939](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-200939)
- `nvidia/nemotron-3-nano-30b-a3b:free`: `4/7`, `24,729` total tokens, run: [20260528-201344](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-201344)
- `qwen/qwen3.5-9b`: `3/7`, `10,320` total tokens, run: [20260528-201123](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-201123)
- `mistralai/mistral-small-24b-instruct-2501`: `2/7`, `3,218` total tokens, run: [20260528-201059](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-201059)
- `mistralai/mistral-nemo`: `2/7`, `18,441` total tokens, run: [20260528-201033](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-201033)
- `amazon/nova-micro-v1`: `2/7`, `35,732` total tokens, run: [20260528-201257](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-201257)
- `google/gemma-3-12b-it`: `1/7`, `6,485` total tokens, run: [20260528-201152](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-201152)

Most important cheap-tier finding:
- `openai/gpt-oss-20b:free` is the strongest economical result seen so far
- it matched the Haiku baseline at `4/7`
- it also matched the larger `gpt-oss-120b:free` result in pass count
- that makes it the best current “cheap systems engineer floor” candidate in this report

Secondary finding:
- `nvidia/nemotron-3-nano-30b-a3b:free` also reached `4/7`, but with somewhat higher token usage and a slightly less clean live-search result profile
- this makes it a credible alternate cheap baseline, though not the current leader

What underperformed:
- `mistral-nemo` and `mistral-small-24b` stayed below the Haiku-like bar in this harness
- `gemma-3-12b-it` was too weak here to be a serious contender for engineering-agent use
- `nova-micro-v1` was not competitive on quality-per-token in this setup

Availability note:
- a broader free-heavy pass also attempted `deepseek/deepseek-v4-flash:free`, but the model was being upstream rate-limited on OpenRouter during evaluation
- that should be treated as a provider-availability issue, not a clean quality score

Practical recommendation from the sweeps:
- if the goal is “Haiku-ish quality at the lowest realistic cost,” start with `openai/gpt-oss-20b:free`
- if free availability becomes unreliable, the paid `openai/gpt-oss-20b` variant is a natural fallback
- `nvidia/nemotron-3-nano-30b-a3b:free` is the next most interesting alternative in this tested set

## Runtime Town Hall

The flat arena is useful, but it still rewards one-shot answer quality more than sustained runtime discipline. To judge `superctx` itself more directly, a second benchmark was added:
- harness: [run_runtime_townhall.py](/Users/deepsaint/Desktop/superctx/arena/run_runtime_townhall.py)
- artifact: [townhall_summary.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-202544-townhall/townhall_summary.json)

Scenario shape:
- exact checkpoint math under an authoritative tool contract
- local repo grounding from docs/source, not vibes
- an incident-command round with distributed-systems stakes
- cross-round state recall
- explicit local-first versus web-first policy judgment

This benchmark is intentionally harsher on the runtime contract than the flat arena. A model can sound smart and still lose if it fails continuity, cites the wrong path form, or ignores the local-grounding discipline.

Town hall leaderboard:
- `openai/gpt-oss-20b:free`: `3/5`, `21,645` total tokens
- `openai/gpt-oss-120b:free`: `2/5`, `35,874` total tokens
- `mistralai/mistral-nemo`: `1/5`, `8,462` total tokens
- `nvidia/nemotron-3-nano-30b-a3b:free`: `1/5`, `15,282` total tokens
- `qwen/qwen3.5-9b`: provider-shape failure on this run, not a clean quality score
- `google/gemma-4-26b-a4b-it:free`: upstream 429 rate-limit failure
- `moonshotai/kimi-k2.6:free`: upstream 429 rate-limit failure
- `minimax/minimax-m2.5:free`: provider reported model-not-found

Most important town hall finding:
- `openai/gpt-oss-20b:free` remained the best low-cost model even when the benchmark shifted away from one-shot tasks and toward runtime continuity
- it passed exact calculation, cross-round recall, and local-first policy discipline
- it still stumbled on the stricter grounding and incident-command rounds, which is exactly the sort of nuanced runtime failure this benchmark is meant to expose

Representative town hall artifacts:
- [openai__gpt-oss-20b__free.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-202544-townhall/openai__gpt-oss-20b__free.json)
- [openai__gpt-oss-120b__free.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-202544-townhall/openai__gpt-oss-120b__free.json)
- [nvidia__nemotron-3-nano-30b-a3b__free.json](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-202544-townhall/nvidia__nemotron-3-nano-30b-a3b__free.json)

What the town hall says about the runtime, not just the models:
- `superctx` is good at preserving exact-tool obedience and simple cross-round state when the model is competent enough to cooperate
- the runtime contract is strong enough that local-first discipline is usually recoverable and measurable
- the hard remaining problem is not “can the runtime say what the rules are”; it is “can the model stay faithfully inside those rules when a multi-step situation gets nuanced”
- this supports the same broad conclusion as the other sweeps: the runtime is carrying its weight, and the dominant remaining variability comes from model quality plus provider behavior

Important caution:
- the town hall is intentionally stricter than the flat arena, so scores are not directly comparable
- provider-level issues showed up more clearly here because the scenario is multi-round and therefore more exposed to shape mismatches and temporary rate limits
- those failures are still useful operationally, because they tell us which cheap providers are actually stable enough for a production runtime layer

### Town Hall Stability Pass

Single-run wins are useful, but they can overstate a model that got lucky on one lap. To judge runtime efficacy more honestly, the top cheap town-hall candidates were rerun three more times:
- [20260528-203751-townhall](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-203751-townhall)
- [20260528-204233-townhall](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-204233-townhall)
- [20260528-204528-townhall](/Users/deepsaint/Desktop/superctx/arena/runs/20260528-204528-townhall)

Repeated cohort:
- `openai/gpt-oss-20b:free`
- `openai/gpt-oss-20b`
- `openai/gpt-oss-120b:free`
- `nvidia/nemotron-3-nano-30b-a3b:free`

Stability summary across the three repeat laps:
- `openai/gpt-oss-120b:free`: average `2.33/5`, range `2..3`, average `20,755` total tokens
- `openai/gpt-oss-20b`: average `2.33/5`, range `2..3`, average `21,429` total tokens
- `openai/gpt-oss-20b:free`: average `2.0/5`, range `2..2`, average `20,059` total tokens
- `nvidia/nemotron-3-nano-30b-a3b:free`: average `1.0/5`, range `1..1`, average `20,643` total tokens

What changed after the stronger pass:
- `gpt-oss-20b:free` stopped looking like a clear outright winner and started looking like a very solid but slightly capped baseline
- the paid `gpt-oss-20b` and `gpt-oss-120b:free` were a little more volatile, but they posted the best repeat average
- `nemotron-3-nano-30b-a3b:free` did not hold up under repetition; its good earlier flat-arena result looks more like a peak than a stable runtime partner

Operational recommendation after the repeat pass:
- if the goal is “best dependable cheap baseline for `superctx`,” `openai/gpt-oss-20b:free` is still the best default
- if slightly more variance is acceptable in exchange for a bit more upside, `openai/gpt-oss-20b` and `openai/gpt-oss-120b:free` are the next best choices
- do not over-read one strong `nemotron` run as stable production behavior

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

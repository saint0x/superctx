# superctx Benchmarks

This file records production-shaped local-model benchmarks for `superctx`.

## Benchmark Thesis

`superctx` should improve weak or raw local-model behavior by spending context
budget on explicit runtime state instead of relying on hidden chat history or
naive prompt stuffing. The important claims are:

- exact-answer discipline should improve when the frame marks a task as exact
- local-grounded answers should cite the relevant durable facts and avoid stale
  distractors
- persistent memory should survive across sessions and be retrievable by scope
- runtime assistance should be measurable against both raw prompting and naive
  memory stuffing

## Local Sock Product Bench

Harness: `arena/run_local_sock_product_bench.py`

Variants:

- `raw`: direct local model prompt with no runtime memory
- `naive_memory`: direct local model prompt with all notes dumped into context
- `superctx`: actual `superctx complete` path using the OpenAI-compatible local
  sock endpoint

Metrics:

- rule score from expected hits, forbidden hits, and exact-output compliance
- variant win count
- request wall clock latency
- raw endpoint token usage where available

Run shape:

```bash
python3 arena/run_local_sock_product_bench.py \
  --base-url http://127.0.0.1:8000 \
  --model Qwen/Qwen3-30B-A3B-GPTQ-Int4
```

Results should be appended below after each production run.

## 2026-07-19 - GMK Qwen3 30B Expanded Adversarial Runtime Bench

Environment:

- Engine: `sock` serving `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- Hardware: GMK Strix Halo / ROCm WSL
- Endpoint: `http://127.0.0.1:8000/v1/chat/completions`
- Server shape: `--max-model-len 4096`, `--gpu-memory-utilization 0.72`, `--enforce-eager`
- Harness run: `/home/deepsaint/work/superctx/arena/runs/20260719-200833-local-sock-product-bench`
- Label: `gmk-qwen3-30b-4096-expanded-adversarial-v6`

Suite expansion:

- Expanded from 4 to 12 scenarios covering exact tool contracts, local path grounding, distractor pressure, cross-round recall, scoped workspace override, canonical build command recall, unknown-secret refusal, stale high-noise conflict, ordered recovery runbooks, multi-hop synthesis, stale-tooling rejection, and session-over-workspace precedence.
- Added explicit tie accounting so equal top scores are recorded as shared wins instead of falling through to dictionary order.
- Tightened compact-prompt exact-answer copying for commands, markers, phrases, codenames, and CLI names.

Summary:

| Variant | Wins | Ties | Mean score | Mean latency |
| --- | ---: | ---: | ---: | ---: |
| `raw` | 0 | 0 | -1.00 | 5.118s |
| `naive_memory` | 0 | 2 | -0.25 | 5.026s |
| `superctx` | 10 | 2 | 3.25 | 1.177s |

Scenario winners:

| Scenario | Winner |
| --- | --- |
| exact tool contract | `superctx` |
| local grounded paths | `superctx` |
| context budget under distractors | `superctx` |
| cross-round recall | tie: `naive_memory`, `superctx` |
| scoped workspace override | `superctx` |
| canonical build contract | `superctx` |
| negative no invention | `superctx` |
| stale high-noise conflict | `superctx` |
| ordered recovery runbook | `superctx` |
| multi-hop synthesis | tie: `naive_memory`, `superctx` |
| stale tooling rejection | `superctx` |
| session vs workspace precedence | `superctx` |

Interpretation:

- Reality: the memory-pack thesis now holds under a broader adversarial suite, not just a small four-case smoke bench.
- Reality: `superctx` is both higher quality and faster here: 10 outright wins, 2 ties, and about 4.27x lower mean latency than naive memory stuffing.
- Reality: the two ties are honest and useful. When the naive prompt has exactly the right compact facts and no harmful conflict, it can match quality, but it still does not beat the `superctx` runtime.
- Current claim: on the local Qwen3 30B sock endpoint, `superctx` materially improves context fidelity and latency versus raw prompting and naive memory stuffing under exact-answer, stale-memory, scoping, and operational-recall pressure.

## 2026-07-19 - GMK Qwen3 30B Optimized Compact Runtime Bench

Environment:

- Engine: `sock` serving `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- Hardware: GMK Strix Halo / ROCm WSL
- Endpoint: `http://127.0.0.1:8000/v1/chat/completions`
- Server shape: `--max-model-len 4096`, `--gpu-memory-utilization 0.72`, `--enforce-eager`
- Harness run: `/home/deepsaint/work/superctx/arena/runs/20260719-192933-local-sock-product-bench`
- Label: `gmk-qwen3-30b-4096-compact-runtime-v2`

Production changes validated by this run:

- Replaced full-frame model prompting with a compact memory-pack prompt that carries only the selected memory, task mode, answer contract, grounding contract, citation requirement, and user request.
- Added exact/literal answer discipline directly to the compact protocol so the model returns only the requested value when the contract requires it.
- Added a deterministic exact-arithmetic fast path for exact tasks that can be computed without spending model tokens.
- Reduced provider `max_tokens` by task mode and set deterministic temperature for repeatable local-model behavior.
- Avoided unnecessary local-path repair calls for valid `src/` and `.brain/` paths.

Summary:

| Variant | Wins | Mean score | Mean latency |
| --- | ---: | ---: | ---: |
| `raw` | 0 | -0.75 | 6.533s |
| `naive_memory` | 1 | 1.25 | 6.243s |
| `superctx` | 3 | 3.00 | 1.483s |

Scenario detail:

| Scenario | Winner | Raw | Naive memory | superctx | superctx latency |
| --- | --- | ---: | ---: | ---: | ---: |
| exact tool contract | `superctx` | -2 | -2 | 3 | 0.070s |
| local grounded paths | `superctx` | 0 | 1 | 2 | 1.272s |
| context budget under distractors | `superctx` | 1 | 3 | 4 | 3.994s |
| cross-round recall | `naive_memory` | -2 | 3 | 3 | 0.595s |

Delta versus the earlier full-frame run:

| Metric | Earlier full-frame `superctx` | Optimized compact `superctx` | Change |
| --- | ---: | ---: | ---: |
| Wins | 2 | 3 | +1 |
| Mean score | 2.50 | 3.00 | +0.50 |
| Mean latency | 31.633s | 1.483s | 21.3x faster |

Interpretation:

- Reality: the memory-pack thesis held while removing most of the previous latency overhead; `superctx` now beats both raw prompting and naive memory on mean quality and mean latency in this bench.
- Reality: the largest speedup comes from not sending the whole frame to the model, not asking the model to compute deterministic exact arithmetic, and sharply bounding completion tokens.
- Reality: `local_grounding_paths` still scores 2 rather than 3 because the response is correct and compact but does not exhaust every scoring nuance.
- Honest thesis: `superctx` is now production-plausible for local-model context discipline under this 4096-token Qwen3 30B setup. The next quality work should expand adversarial memory-ranking cases rather than add more prompt bulk.

## 2026-07-19 - GMK Qwen3 30B 4096-Context Product Bench

Environment:

- Engine: `sock` serving `Qwen/Qwen3-30B-A3B-GPTQ-Int4`
- Hardware: GMK Strix Halo / ROCm WSL
- Endpoint: `http://127.0.0.1:8000/v1/chat/completions`
- Server shape: `--max-model-len 4096`, `--gpu-memory-utilization 0.72`, `--enforce-eager`
- Harness run: `/home/deepsaint/work/superctx/arena/runs/20260719-190616-local-sock-product-bench`

Pre-bench fixes discovered by the run:

- Removed the live adapter dependency on external `jq`; provider response extraction now uses FZY native `json.path`.
- Installed missing `sqlite3` on the GMK because `superctx`'s sqlite-backed memory store could not persist/query memory without it.
- Fixed exact-answer validation to evaluate the visible final answer after `</think>`.
- Routed path-oriented requests through the local-inspection contract instead of the arithmetic exact mode.

Summary:

| Variant | Wins | Mean score | Mean latency |
| --- | ---: | ---: | ---: |
| `raw` | 0 | -0.75 | 6.617s |
| `naive_memory` | 2 | 1.25 | 6.211s |
| `superctx` | 2 | 2.50 | 31.633s |

Scenario detail:

| Scenario | Winner | Raw | Naive memory | superctx |
| --- | --- | ---: | ---: | ---: |
| exact tool contract | `superctx` | -2 | -2 | 3 |
| local grounded paths | `superctx` | 0 | 1 | 2 |
| context budget under distractors | `naive_memory` | 1 | 3 | 2 |
| cross-round recall | `naive_memory` | -2 | 3 | 3 |

Interpretation:

- Reality: once the runtime had sqlite persistence, a 4096-token context window, native JSON extraction, and visible-answer validation, `superctx` produced the highest mean quality score.
- Reality: `superctx` did not dominate every case; naive memory tied or beat it when the task was small enough that dumping all notes was cheap and obvious.
- Reality: `superctx` is materially slower today because it pays for frame construction, richer prompts, and validation/repair.
- Honest thesis: `superctx` is promising for local-model context discipline under exact/local/distractor pressure, but the next production work is latency reduction and stronger memory ranking so it beats naive stuffing even on small synthetic tasks.

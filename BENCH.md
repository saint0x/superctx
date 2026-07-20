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

# superctx

deterministic context runtime for ai agents, implemented in fzy.

## what it is

`superctx` is a production-leaning `SPEC.md` implementation in fzy:

- persistent scoped memory
- explicit brain operations
- deterministic context-frame assembly
- traceable and replayable runtime artifacts
- real adapter execution surfaces
- in-runtime answer validation and repair
- local evaluation harness for tool-using agents

it is not a model, chatbot, or workflow engine.

## current scope

implemented now:

- global, workspace, session, and short/long-term memory modeling
- explicit memory operations in `src/services/brain.fzy`
- context planning in `src/services/planner.fzy`
- sqlite-backed state in `src/services/store.fzy` under `.brain/brain.db`
- sqlite fts-backed retrieval with heuristic fallback
- adapter runtime execution in `src/services/adapters.fzy`
- in-runtime validation / rejection / one-pass repair in `src/services/validator.fzy`
- cli entrypoints and basic http routing
- deterministic fozzy validation and live local-model evaluation harness

not implemented yet:

- semantic retrieval via embeddings or rerankers
- broader live-burned provider validation beyond the openai-compatible path
- richer typed validation policies beyond the current rule-based guardrails

## layout

- `SPEC.md`: design target
- `src/`: runtime, memory, planner, cli, tests
- `config/fzl_system_prompt.md`: operator manual / system prompt
- `arena/eval_model.py`: local model eval harness
- `arena/LIVE_EVAL_REPORT.md`: live agent evaluation summary

## validate

```bash
fz check /Users/deepsaint/Desktop/superctx --json
fz dx-check /Users/deepsaint/Desktop/superctx --strict --json
fz test /Users/deepsaint/Desktop/superctx/src/main.fzy --det --strict-verify --seed 4242 --json
fz doctor project /Users/deepsaint/Desktop/superctx --strict --json
```

for trace-driven validation, use the recorded scenarios under `artifacts/` locally.

## live eval

the arena harness was run against a local openai-compatible endpoint plus aegis-backed browsing.

main result:

- the runtime is in good shape for this scope
- the tested local model was the dominant failure source, not the runtime
- the runtime now makes that distinction explicit by constraining tools, validating outputs, and tracing failures cleanly

see `arena/LIVE_EVAL_REPORT.md`.

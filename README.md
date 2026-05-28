# superctx

deterministic context runtime for ai agents, implemented in fzy.

## what it is

`superctx` is a json-first v0.1 implementation of the `SPEC.md` design:

- persistent scoped memory
- explicit brain operations
- deterministic context-frame assembly
- traceable and replayable runtime artifacts
- adapter and tool metadata surfaces
- local evaluation harness for tool-using agents

it is not a model, chatbot, or workflow engine.

## current scope

implemented now:

- global, workspace, session, and short/long-term memory modeling
- explicit memory operations in `src/services/brain.fzy`
- context planning in `src/services/planner.fzy`
- file-backed state and trace storage in `src/services/store.fzy`
- adapter and tool schema surfaces
- cli entrypoints and basic http routing
- deterministic fozzy validation and live local-model evaluation harness

not implemented yet:

- sqlite-backed storage
- real provider adapter execution inside the fzy runtime
- closed-loop tool orchestration and runtime validation around live model calls

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

- the runtime is in decent shape for a scoped v0.1
- the tested local model was not yet reliable enough to trust as a high-stakes systems or coding agent

see `arena/LIVE_EVAL_REPORT.md`.

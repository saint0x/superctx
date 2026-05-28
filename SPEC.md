# SPEC.md

# FZL — Context Runtime For AI Agents

Version: v0.1

Status: Design

Language Target: fzy

Primary Goal:

Create a deterministic, model-agnostic context runtime that provides persistent memory, scoped knowledge management, context injection, tool orchestration, replayability, and agent self-management for coding agents.

FZL is not an AI model.

FZL is not an agent framework.

FZL is a context operating system that sits between an agent and an inference backend.

The model becomes a replaceable reasoning engine.

The brain, memory, context management, tooling, and runtime remain constant.

---

# Core Thesis

Modern AI agents are largely stateless.

Even when memory exists, it is typically implemented as:

- chat history
- vector retrieval
- hidden system prompts
- ad hoc context injection

FZL introduces a formal runtime where:

- memory is a first-class resource
- context is explicitly managed
- agent state is durable
- model backends are replaceable
- memory operations are observable
- decisions are replayable

The goal is to improve both:

- short-term reasoning quality
- long-term knowledge accumulation

especially for smaller coding models.

---

# Design Principles

## Model Agnostic

Supported today:

- OpenAI APIs
- Anthropic APIs
- Gemini APIs
- DeepSeek APIs

Supported later:

- Ollama
- llama.cpp
- MLX
- vLLM
- custom inference servers

No memory implementation may depend on a specific model vendor.

---

## Brain Portability

An agent's memory must survive:

- model changes
- provider changes
- runtime upgrades
- context window differences

The brain is independent from the model.

---

## Deterministic Operation

All context assembly must be reproducible.

Every session must support:

- replay
- inspection
- auditing
- debugging

---

## Explicit Memory

The agent does not directly own memory.

Memory mutations occur through explicit operations.

Examples:

- remember
- promote
- demote
- compact
- forget
- pin
- unpin

---

## Scoped Knowledge

Not all knowledge is equal.

Memory is divided into distinct scopes.

---

# Memory Architecture

## Global Memory

Knowledge shared across all workspaces.

Examples:

- user preferences
- coding preferences
- architectural patterns
- recurring instructions

Lifetime:

Persistent

---

## Workspace Memory

Knowledge specific to a repository or project.

Examples:

- architecture
- conventions
- build commands
- known bugs
- service relationships

Lifetime:

Persistent

---

## Session Memory

Knowledge specific to an active task.

Examples:

- current objective
- active plan
- recent findings
- active files

Lifetime:

Session

---

## Ephemeral Memory

Scratch space.

Examples:

- hypotheses
- temporary observations
- intermediary reasoning artifacts

Lifetime:

Short-lived

---

## Long-Term Memory

High-confidence durable knowledge.

Examples:

- architectural decisions
- stable invariants
- verified facts

Lifetime:

Persistent

---

## Short-Term Memory

Active working set.

Examples:

- files currently being edited
- current errors
- test outputs

Lifetime:

Task-local

---

# Context Architecture

The model never receives the entire brain.

The runtime constructs a context frame.

## Context Frame

Contains:

- system instructions
- registers
- active stack
- selected memory
- retrieved artifacts
- tool schemas
- user request

The frame is generated immediately before inference.

---

# Runtime Memory Regions

## Registers

Always-hot values.

Examples:

- current goal
- active file
- current workspace
- execution mode

---

## Stack

Task-local context.

Examples:

- current plan
- recent tool outputs
- active findings

---

## Heap

Persistent memory objects.

Examples:

- facts
- summaries
- architectural notes
- invariants

---

## Disk

Durable storage.

Backed by:

- SQLite
- vector index
- traces
- artifacts

---

# Brain Storage

Primary storage:

SQLite

Required properties:

- local-first
- embeddable
- portable
- inspectable
- deterministic

---

# Memory Objects

Every memory entry is represented as a MemoryObject.

Fields:

- id
- scope
- kind
- content
- importance
- confidence
- pinned
- ttl
- provenance
- workspace_id
- session_id
- created_at
- updated_at
- last_accessed_at

---

# Memory Graph

Memory objects may reference one another.

Relationships:

- depends_on
- supports
- contradicts
- summarizes
- replaces
- derived_from

This creates a persistent knowledge graph.

---

# Context Planner

The Context Planner is the most important subsystem.

Responsibilities:

- retrieval
- ranking
- compaction
- injection
- eviction

The planner determines:

What should enter the context window?

---

# Memory Operations

Core runtime operations:

ALLOC
LOAD
PIN
UNPIN
PROMOTE
DEMOTE
APPEND
COMPACT
EVICT
FORGET
QUERY
LINK
SNAPSHOT
RESTORE

All operations are validated before execution.

---

# Tool System

Tools are separate from memory.

Tools operate on:

- filesystem
- git
- shell
- network
- memory

The runtime decides whether tool requests are allowed.

---

# Brain Tools

Built-in brain manipulation tools:

brain.query
brain.remember
brain.update
brain.pin
brain.unpin
brain.promote
brain.demote
brain.compact
brain.forget
brain.snapshot
brain.restore

These allow agents to modify their own state.

---

# Thin Runtime Prompt

The system prompt is intentionally minimal.

Purpose:

Teach the model how to operate inside FZL.

The prompt is not memory.

The prompt is not state.

The prompt is a user manual.

Responsibilities:

- explain memory scopes
- explain tool usage
- explain persistence behavior
- explain runtime rules

The actual brain remains external.

---

# Inference Pipeline

1. User request arrives
2. Session starts
3. Context planner executes
4. Memory selected
5. Context frame compiled
6. Model inference executed
7. Tool requests parsed
8. Memory operations parsed
9. Runtime validation
10. State committed
11. Trace recorded

---

# Model Adapter Layer

The runtime communicates through adapters.

Required adapters:

OpenAIAdapter
AnthropicAdapter
GeminiAdapter
DeepSeekAdapter
OllamaAdapter
LlamaCppAdapter
MLXAdapter
VLLMAdapter

All adapters expose a unified interface.

---

# Replay System

Every session must be replayable.

Artifacts:

session.trace.json
memory.diff.json
context.frame.json
tool.events.json
inference.events.json

Goals:

- debugging
- benchmarking
- regression testing
- agent evaluation

---

# SDK Design

High-level SDK:

fzy let runtime = fzl.runtime()  let brain = runtime.brain()  brain.workspace.remember(     "repo.arch",     "Service-oriented architecture" )  let agent = runtime.agent("coder")  agent.ask(     "Fix the authentication bug." ) 

The SDK should feel idiomatic to fzy and expose explicit ownership and lifecycle semantics where appropriate.

---

# Future Goals

## Local Models

Support small coding models.

Target outcome:

A smaller model equipped with:

- persistent memory
- context planning
- retrieval
- scoped knowledge
- self-management

should outperform a larger stateless model on long-running coding tasks.

---

## Multi-Agent Memory

Allow multiple agents to share:

- workspace memory
- architectural memory
- project memory

while retaining private session memory.

---

## Distributed Brain

Eventually support:

- SQLite
- Postgres
- replicated memory stores

without changing the runtime API.

---

# Non-Goals

FZL is not:

- a vector database
- a model provider
- a chatbot UI
- a workflow engine
- a replacement for inference servers

FZL exists to manage context, memory, and agent state.

Everything else is replaceable.

---

# Final Definition

FZL is a Context Runtime for AI Agents.

Models reason.

Brains remember.

The Context Planner decides what matters.

The Runtime enforces the rules.
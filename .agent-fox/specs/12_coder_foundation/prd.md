# PRD: Coder Foundation & Provider Layer

## Intent

Establish the package scaffolding, multi-model LLM provider abstraction, prompt
template system, and CLI entry point for the `coder` tool — a spec-driven
coding agent that can run against different LLM providers to compare how each
model implements the same specification.

## Goals

1. Create a new `packages/coder/` package in the af-core monorepo with proper
   uv workspace integration.
2. Provide a unified LLM provider abstraction using LangChain chat models that
   supports Anthropic (Claude), Google (Gemini), and Ollama (local open-source
   models) through a single interface.
3. Implement a filesystem-based prompt template system with 3-layer assembly
   (base profile + persona profile + task context), inspired by agent-fox's
   profile loading pattern.
4. Deliver a Click-based CLI entry point (`coder run`) that accepts a campaign
   directory, model name, and target repository path.
5. Set up structured verbose logging from the start so every subsequent spec
   has observability infrastructure available.

## Non-Goals

- No LangGraph workflow in this spec (deferred to spec 14).
- No spec reading or dependency analysis (deferred to spec 13).
- No circuit breakers or safety mechanisms (deferred to spec 15).
- No worktree or git operations (deferred to spec 14).
- No comparison mode or multi-run orchestration — single-run, single-model.
- No Claude Agent SDK integration — LangChain tools only.

## Background

The af-core project uses spec-driven development: specifications define what to
build, and agents execute the implementation. Spec 11 plans an execution engine
(`afrunner`) using Claude Agent SDK. This new `coder` package is a fully
independent parallel experiment that uses LangChain/LangGraph instead, enabling
multi-model comparison.

The agent-fox project demonstrates a proven 3-layer prompt assembly pattern:
base agent profile → archetype (persona) profile → task context. Prompt
templates are editable markdown files on the filesystem, not hardcoded in
Python. Project-level templates override package defaults. This pattern should
be replicated in the coder package.

## Design Decisions

1. **LangChain for provider abstraction**: LangChain's chat model interfaces
   (`ChatAnthropic`, `ChatGoogleGenerativeAI`, `ChatOllama`) provide a uniform
   API across all three provider types. This is the simplest path to
   multi-model support.
2. **Ollama for local models**: Ollama is the most popular local inference
   server with broad model support and an OpenAI-compatible API. It's the
   default local model backend.
3. **Fully independent from spec 11**: The coder package shares only `afspec`
   for spec format models. It does not depend on `afrunner`, `afprompt`,
   `speclib`, or `spec-cli`.
4. **Filesystem prompt templates**: Templates are `.md` files in a configurable
   directory. Package ships default templates; projects can override them.
   Variables are substituted using Python's `string.Template` (simple `$var`
   syntax) — no Jinja2 dependency.
5. **structlog for logging**: Structured logging with human-readable console
   output (via `structlog` + `rich`). Verbose by default.
6. **No `afsec` package**: The user mentioned `afsec` but it does not exist.
   The package to reuse is `afspec` (spec format models and discovery).
7. **Configuration precedence**: Project `.coder.yaml` > user `~/.coder/config.yaml` > environment variables > defaults.

## Source

Source: Input provided by user via interactive prompt.

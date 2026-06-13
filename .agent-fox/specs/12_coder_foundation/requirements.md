# Requirements Document

## Introduction

This document specifies the foundation layer for the `coder` tool — a
spec-driven coding agent that supports multiple LLM providers. It covers
package structure, provider abstraction, prompt template system, CLI entry
point, and structured logging.

## Glossary

- **Provider**: An LLM service backend (Anthropic, Google, Ollama) accessed
  through a LangChain chat model interface.
- **Provider Registry**: A mapping from model names to configured LangChain
  chat model instances.
- **Prompt Template**: A markdown file on the filesystem containing a prompt
  with `$variable` placeholders for substitution.
- **Persona Profile**: A prompt template that defines an agent's role and
  behavioral instructions (e.g., `coder.md`, `reviewer.md`).
- **Layered Assembly**: The process of composing a final system prompt from
  three layers: base profile, persona profile, and task context.
- **Base Profile**: The foundational agent identity template (`agent.md`),
  loaded as the first prompt layer.
- **Task Context**: The third prompt layer containing spec-specific information
  (requirements, test specs, subtask details) for the current work unit.
- **Campaign Directory**: A filesystem directory containing one or more spec
  pack folders.
- **Spec Pack**: A folder containing the five spec artifacts (`prd.md`,
  `requirements.json`, `test_spec.json`, `tasks.json`, and optionally
  `design.json`).
- **Model Name**: A string identifier for an LLM model (e.g.,
  `claude-opus-4-6`, `gemini-2.5-pro`, `codestral:latest`).

## Requirements

### Requirement 1: Package Structure

**User Story:** As a developer, I want the coder package to follow the
monorepo conventions, so that it integrates cleanly with existing tooling.

#### Acceptance Criteria

[12-REQ-1.1] THE coder package SHALL reside at `packages/coder/` with source
code in `packages/coder/coder/` and tests in `packages/coder/tests/`.

[12-REQ-1.2] THE coder package SHALL have a `pyproject.toml` that declares it
as a uv workspace member with dependencies on `afspec`, `langchain`,
`langchain-anthropic`, `langchain-google-genai`, `langchain-ollama`, `click`,
`rich`, `pydantic`, and `structlog`.

[12-REQ-1.3] THE root `pyproject.toml` SHALL include `coder` as a workspace
member under `[tool.uv.workspace]`.

#### Edge Cases

[12-REQ-1.E1] IF the `packages/coder/` directory already exists, THEN THE
build system SHALL raise an error during `uv sync` rather than silently
overwriting.

---

### Requirement 2: LLM Provider Abstraction

**User Story:** As a user, I want to run the same coding workflow against
different LLM models, so that I can compare their output quality.

#### Acceptance Criteria

[12-REQ-2.1] THE system SHALL provide an `LLMProvider` interface that wraps
a LangChain `BaseChatModel` and exposes a method to invoke the model with
messages and tools, returning a response with content and tool calls.

[12-REQ-2.2] THE system SHALL implement `AnthropicProvider` using
`ChatAnthropic` from `langchain-anthropic`, supporting model names prefixed
with `claude-` (e.g., `claude-opus-4-6`).

[12-REQ-2.3] THE system SHALL implement `GoogleProvider` using
`ChatGoogleGenerativeAI` from `langchain-google-genai`, supporting model
names prefixed with `gemini-` (e.g., `gemini-2.5-pro`).

[12-REQ-2.4] THE system SHALL implement `OllamaProvider` using `ChatOllama`
from `langchain-ollama`, supporting any model name available in the local
Ollama instance.

[12-REQ-2.5] WHEN a provider is instantiated, THE system SHALL validate that
required credentials are available (API key for Anthropic/Google, running
Ollama server for Ollama) AND return a clear error message if validation
fails.

#### Edge Cases

[12-REQ-2.E1] IF the Ollama server is not reachable at the configured URL,
THEN THE system SHALL raise a `ProviderConnectionError` with the URL and
connection details.

[12-REQ-2.E2] IF an API key environment variable is empty or unset for
Anthropic or Google providers, THEN THE system SHALL raise a
`ProviderConfigError` listing the expected environment variable name.

---

### Requirement 3: Provider Registry

**User Story:** As a user, I want to specify a model name on the command line
and have the system automatically create the correct provider, so that I don't
need to know provider-specific configuration details.

#### Acceptance Criteria

[12-REQ-3.1] THE system SHALL provide a `ProviderRegistry` that maps model
name patterns to provider constructors AND returns a configured `LLMProvider`
instance for a given model name.

[12-REQ-3.2] WHEN a model name starts with `claude-`, THE registry SHALL
create an `AnthropicProvider` with that model name.

[12-REQ-3.3] WHEN a model name starts with `gemini-`, THE registry SHALL
create a `GoogleProvider` with that model name.

[12-REQ-3.4] WHEN a model name does not match any known prefix, THE registry
SHALL attempt to create an `OllamaProvider` with that model name as the
Ollama model tag.

[12-REQ-3.5] THE registry SHALL allow users to register custom model-name
to provider mappings via configuration, overriding the default prefix-based
resolution.

#### Edge Cases

[12-REQ-3.E1] IF the model name is an empty string, THEN THE registry SHALL
raise a `ValueError` with a descriptive message.

---

### Requirement 4: Configuration System

**User Story:** As a user, I want to configure the coder tool via YAML files
and environment variables, so that I can set defaults and override per-run.

#### Acceptance Criteria

[12-REQ-4.1] THE system SHALL load configuration from the following sources
in precedence order (highest first): environment variables, project-level
`.coder.yaml`, user-level `~/.coder/config.yaml`, built-in defaults.

[12-REQ-4.2] THE configuration SHALL support the following keys: `model`
(default model name), `templates_dir` (path to prompt templates),
`ollama_url` (Ollama server URL, default `http://localhost:11434`),
`log_level` (default `DEBUG`), `log_file` (optional file path).

[12-REQ-4.3] THE system SHALL support environment variable overrides using
the prefix `CODER_`: `CODER_MODEL`, `CODER_TEMPLATES_DIR`, `CODER_OLLAMA_URL`,
`CODER_LOG_LEVEL`, `CODER_LOG_FILE`.

[12-REQ-4.4] WHEN both a YAML config file and an environment variable set the
same key, THE system SHALL use the environment variable value.

[12-REQ-4.5] THE system SHALL return a frozen pydantic `CoderConfig` dataclass
with all resolved configuration values AND validate types at load time.

#### Edge Cases

[12-REQ-4.E1] IF a YAML config file contains unknown keys, THEN THE system
SHALL log a warning for each unknown key and ignore it.

[12-REQ-4.E2] IF no config file exists at any search path, THEN THE system
SHALL use built-in defaults without error.

[12-REQ-4.E3] IF a config file contains invalid YAML syntax, THEN THE system
SHALL raise a `ConfigError` with the file path and parse error details.

---

### Requirement 5: Prompt Template Loading

**User Story:** As a user, I want prompt templates to be editable markdown
files on disk, so that I can customize agent behavior without modifying code.

#### Acceptance Criteria

[12-REQ-5.1] THE system SHALL load prompt templates from a configurable
templates directory, defaulting to `coder/_templates/` within the package.

[12-REQ-5.2] WHEN a template is requested by name (e.g., `coder`), THE system
SHALL search for `{name}.md` in the following order: project-level
`.coder/templates/`, then package-level `coder/_templates/`, AND return the
content of the first match.

[12-REQ-5.3] THE system SHALL strip YAML frontmatter (delimited by `---`)
from template files before returning the content.

[12-REQ-5.4] THE system SHALL validate template names against the pattern
`^[a-zA-Z0-9_-]+$` to prevent path traversal AND reject names containing
path separators or `..`.

[12-REQ-5.5] THE system SHALL reject symlinks during template resolution
AND raise a `TemplateSecurityError` if a symlink is encountered.

[12-REQ-5.6] THE system SHALL ship default templates for `agent` (base
profile), `coder` (coding persona), and `reviewer` (intent verification
persona).

#### Edge Cases

[12-REQ-5.E1] IF a requested template name does not exist in any search
path, THEN THE system SHALL raise a `TemplateNotFoundError` listing the
paths that were searched.

[12-REQ-5.E2] IF a template file is empty (zero bytes), THEN THE system
SHALL return an empty string without error.

---

### Requirement 6: Layered Prompt Assembly

**User Story:** As a developer, I want system prompts composed from multiple
layers, so that different personas and task contexts can be combined
consistently.

#### Acceptance Criteria

[12-REQ-6.1] WHEN assembling a system prompt, THE system SHALL compose three
layers in order: base profile (from `agent.md`), persona profile (from
`{persona}.md`), and task context (provided as a string) AND return the
concatenated result with double-newline separators.

[12-REQ-6.2] WHEN the base profile template (`agent.md`) does not exist, THE
system SHALL skip layer 1 and compose only persona + task context.

[12-REQ-6.3] THE system SHALL substitute `$variable` placeholders in templates
using Python `string.Template` with the provided variables dictionary AND
leave unrecognized placeholders unchanged (safe substitution).

[12-REQ-6.4] THE `assemble_prompt` function SHALL accept parameters for
persona name, task context string, and an optional variables dictionary AND
return the assembled prompt string.

#### Edge Cases

[12-REQ-6.E1] IF the variables dictionary contains a key not present in any
template, THEN THE system SHALL ignore the extra key without error.

---

### Requirement 7: CLI Entry Point

**User Story:** As a user, I want a `coder` command-line tool to run the
coding agent, so that I can execute spec-driven coding from my terminal.

#### Acceptance Criteria

[12-REQ-7.1] THE system SHALL provide a `coder` CLI command group registered
as a console script entry point in `pyproject.toml`.

[12-REQ-7.2] THE `coder run` subcommand SHALL accept the following arguments:
`campaign_dir` (required, path to campaign directory), `--model` (optional,
model name, defaults to config), `--repo` (optional, target repo path,
defaults to current directory).

[12-REQ-7.3] WHEN `coder run` is invoked, THE system SHALL load configuration,
create the provider from the model name, validate the campaign directory
exists, and log the run parameters AND return exit code 0 on success or 1
on error.

[12-REQ-7.4] THE `coder models` subcommand SHALL list all known model name
prefixes and their associated providers AND print them in a formatted table.

[12-REQ-7.5] WHEN `coder run` is invoked with `--help`, THE system SHALL
display usage information for all arguments and options.

#### Edge Cases

[12-REQ-7.E1] IF the campaign directory path does not exist, THEN THE CLI
SHALL print an error message to stderr and exit with code 1.

[12-REQ-7.E2] IF the `--model` argument is provided but the provider cannot
be created (e.g., missing API key), THEN THE CLI SHALL print the provider
error message to stderr and exit with code 1.

---

### Requirement 8: Structured Logging

**User Story:** As a user, I want verbose logging by default, so that I can
see what the coding agent is doing in real time.

#### Acceptance Criteria

[12-REQ-8.1] THE system SHALL configure `structlog` with `rich` console
rendering, producing human-readable timestamped log output to stderr.

[12-REQ-8.2] THE system SHALL log at `DEBUG` level by default, configurable
via the `log_level` configuration key.

[12-REQ-8.3] WHERE `log_file` is configured, THE system SHALL write log
output to the specified file in addition to the console.

[12-REQ-8.4] THE system SHALL include the following context fields in every
log event: `timestamp`, `level`, `module`, `event`.

[12-REQ-8.5] THE system SHALL provide a `get_logger(name)` function that
returns a bound structlog logger with the given module name.

#### Edge Cases

[12-REQ-8.E1] IF the log file path is not writable, THEN THE system SHALL
log a warning to stderr and continue with console-only logging.

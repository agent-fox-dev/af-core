# Test Specification: Coder Foundation & Provider Layer

## Overview

Tests are organized by module, mapping each acceptance criterion and
correctness property to a concrete test contract. Unit tests use mocked
LangChain chat models and temporary directories. Property tests use
Hypothesis for input generation. Integration tests use Click's test runner
for CLI validation.

## Test Cases

### TS-12-1: Package structure exists

**Requirement:** 12-REQ-1.1
**Type:** unit
**Description:** Verify the coder package is importable and has the expected
module structure.

**Preconditions:**
- Package installed in development mode via `uv sync`.

**Input:**
- Import `coder` package.

**Expected:**
- Import succeeds without error.
- `coder.__name__` equals `"coder"`.

**Assertion pseudocode:**
```
import coder
ASSERT coder.__name__ == "coder"
```

---

### TS-12-2: Pyproject declares workspace dependencies

**Requirement:** 12-REQ-1.2
**Type:** unit
**Description:** Verify pyproject.toml lists required dependencies.

**Preconditions:**
- `packages/coder/pyproject.toml` exists.

**Input:**
- Read and parse pyproject.toml.

**Expected:**
- Dependencies include: afspec, langchain, langchain-anthropic,
  langchain-google-genai, langchain-ollama, click, rich, pydantic, structlog.

**Assertion pseudocode:**
```
toml = parse_toml("packages/coder/pyproject.toml")
deps = toml["project"]["dependencies"]
FOR EACH required IN ["afspec", "langchain", "click", "rich", "pydantic", "structlog"]:
    ASSERT any(required in dep for dep in deps)
```

---

### TS-12-3: AnthropicProvider wraps ChatAnthropic

**Requirement:** 12-REQ-2.2
**Type:** unit
**Description:** Verify AnthropicProvider creates a ChatAnthropic instance
with the given model name.

**Preconditions:**
- `ANTHROPIC_API_KEY` environment variable set to a test value.

**Input:**
- Create `AnthropicProvider(model_name="claude-opus-4-6")`.

**Expected:**
- Provider's underlying chat model is a `ChatAnthropic` instance.
- Provider's `model_name` attribute equals `"claude-opus-4-6"`.

**Assertion pseudocode:**
```
provider = AnthropicProvider("claude-opus-4-6")
ASSERT isinstance(provider._chat_model, ChatAnthropic)
ASSERT provider.model_name == "claude-opus-4-6"
```

---

### TS-12-4: GoogleProvider wraps ChatGoogleGenerativeAI

**Requirement:** 12-REQ-2.3
**Type:** unit
**Description:** Verify GoogleProvider creates a ChatGoogleGenerativeAI
instance.

**Preconditions:**
- `GOOGLE_API_KEY` environment variable set to a test value.

**Input:**
- Create `GoogleProvider(model_name="gemini-2.5-pro")`.

**Expected:**
- Provider's underlying chat model is a `ChatGoogleGenerativeAI` instance.
- Provider's `model_name` attribute equals `"gemini-2.5-pro"`.

**Assertion pseudocode:**
```
provider = GoogleProvider("gemini-2.5-pro")
ASSERT isinstance(provider._chat_model, ChatGoogleGenerativeAI)
ASSERT provider.model_name == "gemini-2.5-pro"
```

---

### TS-12-5: OllamaProvider wraps ChatOllama

**Requirement:** 12-REQ-2.4
**Type:** unit
**Description:** Verify OllamaProvider creates a ChatOllama instance.

**Preconditions:**
- None (Ollama does not require API key at construction time).

**Input:**
- Create `OllamaProvider(model_name="codestral:latest")`.

**Expected:**
- Provider's underlying chat model is a `ChatOllama` instance.
- Provider's `model_name` attribute equals `"codestral:latest"`.

**Assertion pseudocode:**
```
provider = OllamaProvider("codestral:latest")
ASSERT isinstance(provider._chat_model, ChatOllama)
ASSERT provider.model_name == "codestral:latest"
```

---

### TS-12-6: Provider validates credentials on construction

**Requirement:** 12-REQ-2.5
**Type:** unit
**Description:** Verify providers check for required credentials.

**Preconditions:**
- `ANTHROPIC_API_KEY` environment variable is unset.

**Input:**
- Attempt to create `AnthropicProvider("claude-opus-4-6")`.

**Expected:**
- Raises `ProviderConfigError` mentioning `ANTHROPIC_API_KEY`.

**Assertion pseudocode:**
```
unset_env("ANTHROPIC_API_KEY")
ASSERT_RAISES ProviderConfigError:
    AnthropicProvider("claude-opus-4-6")
```

---

### TS-12-7: Registry resolves claude- prefix to Anthropic

**Requirement:** 12-REQ-3.2
**Type:** unit
**Description:** Verify registry maps claude- prefix to AnthropicProvider.

**Preconditions:**
- `ANTHROPIC_API_KEY` set to a test value.

**Input:**
- `ProviderRegistry().resolve("claude-opus-4-6")`.

**Expected:**
- Returns an `AnthropicProvider` instance.

**Assertion pseudocode:**
```
registry = ProviderRegistry()
provider = registry.resolve("claude-opus-4-6")
ASSERT isinstance(provider, AnthropicProvider)
```

---

### TS-12-8: Registry resolves gemini- prefix to Google

**Requirement:** 12-REQ-3.3
**Type:** unit
**Description:** Verify registry maps gemini- prefix to GoogleProvider.

**Preconditions:**
- `GOOGLE_API_KEY` set to a test value.

**Input:**
- `ProviderRegistry().resolve("gemini-2.5-pro")`.

**Expected:**
- Returns a `GoogleProvider` instance.

**Assertion pseudocode:**
```
registry = ProviderRegistry()
provider = registry.resolve("gemini-2.5-pro")
ASSERT isinstance(provider, GoogleProvider)
```

---

### TS-12-9: Registry falls back to Ollama for unknown prefix

**Requirement:** 12-REQ-3.4
**Type:** unit
**Description:** Verify unknown model names are sent to Ollama.

**Preconditions:**
- None.

**Input:**
- `ProviderRegistry().resolve("codestral:latest")`.

**Expected:**
- Returns an `OllamaProvider` instance.

**Assertion pseudocode:**
```
registry = ProviderRegistry()
provider = registry.resolve("codestral:latest")
ASSERT isinstance(provider, OllamaProvider)
```

---

### TS-12-10: Config loads from YAML file

**Requirement:** 12-REQ-4.1
**Type:** unit
**Description:** Verify config is loaded from a YAML file.

**Preconditions:**
- Temporary `.coder.yaml` file with `model: gemini-2.5-pro`.

**Input:**
- Call `load_config(project_dir=tmp_dir)`.

**Expected:**
- `config.model` equals `"gemini-2.5-pro"`.

**Assertion pseudocode:**
```
write_file(tmp_dir / ".coder.yaml", "model: gemini-2.5-pro\n")
config = load_config(project_dir=tmp_dir)
ASSERT config.model == "gemini-2.5-pro"
```

---

### TS-12-11: Env vars override YAML config

**Requirement:** 12-REQ-4.4
**Type:** unit
**Description:** Verify environment variables take precedence over YAML.

**Preconditions:**
- Temporary `.coder.yaml` with `model: gemini-2.5-pro`.
- `CODER_MODEL=claude-opus-4-6` in environment.

**Input:**
- Call `load_config(project_dir=tmp_dir)`.

**Expected:**
- `config.model` equals `"claude-opus-4-6"`.

**Assertion pseudocode:**
```
write_file(tmp_dir / ".coder.yaml", "model: gemini-2.5-pro\n")
set_env("CODER_MODEL", "claude-opus-4-6")
config = load_config(project_dir=tmp_dir)
ASSERT config.model == "claude-opus-4-6"
```

---

### TS-12-12: Template loader finds package defaults

**Requirement:** 12-REQ-5.1, 12-REQ-5.6
**Type:** unit
**Description:** Verify default templates are loadable from the package.

**Preconditions:**
- Package installed with `_templates/` directory.

**Input:**
- `TemplateLoader().load("coder")`.

**Expected:**
- Returns non-empty string content.
- Content does not contain YAML frontmatter delimiters.

**Assertion pseudocode:**
```
loader = TemplateLoader()
content = loader.load("coder")
ASSERT len(content) > 0
ASSERT not content.startswith("---")
```

---

### TS-12-13: Template loader prefers project-level override

**Requirement:** 12-REQ-5.2
**Type:** unit
**Description:** Verify project templates override package defaults.

**Preconditions:**
- Temporary project directory with `.coder/templates/coder.md` containing
  "Custom coder prompt".

**Input:**
- `TemplateLoader(project_dir=tmp_dir).load("coder")`.

**Expected:**
- Returns `"Custom coder prompt"`.

**Assertion pseudocode:**
```
write_file(tmp_dir / ".coder/templates/coder.md", "Custom coder prompt")
loader = TemplateLoader(project_dir=tmp_dir)
content = loader.load("coder")
ASSERT content == "Custom coder prompt"
```

---

### TS-12-14: Template loader strips frontmatter

**Requirement:** 12-REQ-5.3
**Type:** unit
**Description:** Verify YAML frontmatter is removed from templates.

**Preconditions:**
- Template file with frontmatter: `---\nname: test\n---\nActual content`.

**Input:**
- Load the template.

**Expected:**
- Returns `"Actual content"` (no frontmatter).

**Assertion pseudocode:**
```
write_file(tmp_dir / ".coder/templates/test.md", "---\nname: test\n---\nActual content")
loader = TemplateLoader(project_dir=tmp_dir)
content = loader.load("test")
ASSERT content == "Actual content"
```

---

### TS-12-15: Prompt assembler composes three layers

**Requirement:** 12-REQ-6.1
**Type:** unit
**Description:** Verify 3-layer prompt assembly with correct ordering.

**Preconditions:**
- Templates: `agent.md` = "Base", `coder.md` = "Persona".

**Input:**
- `PromptAssembler.assemble(persona="coder", task_context="Context")`.

**Expected:**
- Result equals `"Base\n\nPersona\n\nContext"`.

**Assertion pseudocode:**
```
assembler = PromptAssembler(loader)
result = assembler.assemble(persona="coder", task_context="Context")
ASSERT result == "Base\n\nPersona\n\nContext"
```

---

### TS-12-16: Prompt assembler skips missing base profile

**Requirement:** 12-REQ-6.2
**Type:** unit
**Description:** Verify assembly works without a base profile.

**Preconditions:**
- No `agent.md` template exists. `coder.md` = "Persona".

**Input:**
- `PromptAssembler.assemble(persona="coder", task_context="Context")`.

**Expected:**
- Result equals `"Persona\n\nContext"`.

**Assertion pseudocode:**
```
assembler = PromptAssembler(loader_without_agent)
result = assembler.assemble(persona="coder", task_context="Context")
ASSERT result == "Persona\n\nContext"
```

---

### TS-12-17: CLI run command validates campaign directory

**Requirement:** 12-REQ-7.1, 12-REQ-7.3
**Type:** integration
**Description:** Verify `coder run` with a valid campaign dir succeeds.

**Preconditions:**
- Temporary campaign directory exists.

**Input:**
- Invoke `coder run <tmp_campaign_dir> --model claude-opus-4-6`.

**Expected:**
- Exit code 0.
- Output contains run parameters.

**Assertion pseudocode:**
```
result = cli_runner.invoke(["run", str(tmp_campaign_dir), "--model", "claude-opus-4-6"])
ASSERT result.exit_code == 0
```

---

### TS-12-18: CLI run rejects missing campaign directory

**Requirement:** 12-REQ-7.E1
**Type:** integration
**Description:** Verify `coder run` fails for nonexistent directory.

**Preconditions:**
- None.

**Input:**
- Invoke `coder run /nonexistent/path`.

**Expected:**
- Exit code 1.
- Stderr contains error message about missing directory.

**Assertion pseudocode:**
```
result = cli_runner.invoke(["run", "/nonexistent/path"])
ASSERT result.exit_code == 1
ASSERT "not exist" in result.output or "not found" in result.output
```

---

### TS-12-19: Structured logging produces console output

**Requirement:** 12-REQ-8.1, 12-REQ-8.4
**Type:** unit
**Description:** Verify logging setup produces structured output.

**Preconditions:**
- None.

**Input:**
- Set up logging, emit a log event.

**Expected:**
- Console output contains timestamp, level, module name, and event message.

**Assertion pseudocode:**
```
setup_logging(config)
logger = get_logger("test_module")
logger.info("test_event", key="value")
-- verify output captured to stderr contains "test_event"
```

## Property Test Cases

### TS-12-P1: Provider resolution is deterministic

**Property:** Property 1 from design.md
**Validates:** 12-REQ-3.2, 12-REQ-3.3, 12-REQ-3.4
**Type:** property
**Description:** For any model name, the registry always resolves to the
same provider type.

**For any:** model name string generated by Hypothesis (text strategy with
constraints: non-empty, printable ASCII)
**Invariant:** If model name starts with `claude-`, result is
AnthropicProvider. If starts with `gemini-`, result is GoogleProvider.
Otherwise, result is OllamaProvider.

**Assertion pseudocode:**
```
FOR ANY model_name IN text(min_size=1, alphabet=printable_ascii):
    registry = ProviderRegistry()
    provider = registry.resolve(model_name)
    IF model_name.startswith("claude-"):
        ASSERT isinstance(provider, AnthropicProvider)
    ELIF model_name.startswith("gemini-"):
        ASSERT isinstance(provider, GoogleProvider)
    ELSE:
        ASSERT isinstance(provider, OllamaProvider)
```

---

### TS-12-P2: Configuration precedence holds

**Property:** Property 2 from design.md
**Validates:** 12-REQ-4.1, 12-REQ-4.4
**Type:** property
**Description:** Environment variables always override YAML config values.

**For any:** model name string (non-empty ASCII), YAML model value (non-empty
ASCII), where the two differ
**Invariant:** The resolved config's model field equals the environment
variable value, not the YAML value.

**Assertion pseudocode:**
```
FOR ANY env_model, yaml_model IN text(min_size=1) WHERE env_model != yaml_model:
    write_file(tmp / ".coder.yaml", f"model: {yaml_model}")
    set_env("CODER_MODEL", env_model)
    config = load_config(project_dir=tmp)
    ASSERT config.model == env_model
```

---

### TS-12-P3: Template names are path-traversal safe

**Property:** Property 3 from design.md
**Validates:** 12-REQ-5.4, 12-REQ-5.5
**Type:** property
**Description:** Any template name containing path separators or traversal
sequences is rejected.

**For any:** template name containing `/`, `\`, or `..` (generated by
injecting path components into random strings)
**Invariant:** `TemplateLoader.load(name)` raises an error.

**Assertion pseudocode:**
```
FOR ANY name IN text() COMBINED WITH sampled_from(["/", "\\", ".."]):
    ASSERT_RAISES (ValueError or TemplateSecurityError):
        TemplateLoader().load(name)
```

---

### TS-12-P4: Prompt assembly preserves layer order

**Property:** Property 4 from design.md
**Validates:** 12-REQ-6.1, 12-REQ-6.2
**Type:** property
**Description:** The assembled prompt always contains persona content before
task context, and base content (if present) before persona.

**For any:** persona content string (non-empty), task context string
(non-empty), optional base content string
**Invariant:** In the assembled result, persona content appears before task
context. If base content is non-empty, it appears before persona content.

**Assertion pseudocode:**
```
FOR ANY persona_text, task_context IN text(min_size=1):
    result = assemble(persona_text, task_context)
    ASSERT result.index(persona_text) < result.index(task_context)
```

---

### TS-12-P5: Safe substitution leaves unknown placeholders

**Property:** Property 5 from design.md
**Validates:** 12-REQ-6.3, 12-REQ-6.E1
**Type:** property
**Description:** Template substitution replaces known variables and leaves
unknown `$placeholders` unchanged.

**For any:** template with `$known` and `$unknown` placeholders, variables
dict containing only `known`
**Invariant:** Result contains the value of `known` and the literal string
`$unknown`.

**Assertion pseudocode:**
```
FOR ANY known_val IN text(min_size=1):
    template = "Hello $known, meet $unknown"
    result = substitute(template, {"known": known_val})
    ASSERT known_val in result
    ASSERT "$unknown" in result
```

### TS-12-20: Root pyproject includes coder as workspace member

**Requirement:** 12-REQ-1.3
**Type:** unit
**Description:** Verify the root `pyproject.toml` lists `packages/coder` as a
uv workspace member.

**Preconditions:**
- Root `pyproject.toml` exists.

**Input:**
- Read and parse root `pyproject.toml`.

**Expected:**
- `[tool.uv.workspace]` members list contains `"packages/coder"`.

**Assertion pseudocode:**
```
toml = parse_toml("pyproject.toml")
members = toml["tool"]["uv"]["workspace"]["members"]
ASSERT "packages/coder" in members
```

---

### TS-12-21: LLMProvider interface exposes required methods

**Requirement:** 12-REQ-2.1
**Type:** unit
**Description:** Verify the `LLMProvider` interface defines `model_name`,
`invoke()`, and `validate()`.

**Preconditions:**
- `coder.providers` module importable.

**Input:**
- Import `LLMProvider` from `coder.providers`.

**Expected:**
- `LLMProvider` has attributes/methods: `model_name`, `invoke`, `validate`.

**Assertion pseudocode:**
```
from coder.providers import LLMProvider
ASSERT hasattr(LLMProvider, "model_name")
ASSERT hasattr(LLMProvider, "invoke")
ASSERT hasattr(LLMProvider, "validate")
```

---

### TS-12-22: ProviderRegistry returns configured LLMProvider

**Requirement:** 12-REQ-3.1
**Type:** unit
**Description:** Verify `ProviderRegistry` maps model name patterns to provider
constructors and returns a configured `LLMProvider` instance.

**Preconditions:**
- `ANTHROPIC_API_KEY` set to a test value.

**Input:**
- `ProviderRegistry().resolve("claude-opus-4-6")`.

**Expected:**
- Returns an object that implements the `LLMProvider` interface.
- The returned provider's `model_name` equals `"claude-opus-4-6"`.

**Assertion pseudocode:**
```
registry = ProviderRegistry()
provider = registry.resolve("claude-opus-4-6")
ASSERT hasattr(provider, "model_name")
ASSERT hasattr(provider, "invoke")
ASSERT provider.model_name == "claude-opus-4-6"
```

---

### TS-12-23: Registry allows custom model-to-provider mappings

**Requirement:** 12-REQ-3.5
**Type:** unit
**Description:** Verify users can register custom prefix-to-provider mappings
that override the default resolution.

**Preconditions:**
- A mock provider constructor.

**Input:**
- Register custom prefix `"custom-"` with a mock constructor.
- Resolve `"custom-model"`.

**Expected:**
- Returns an instance created by the mock constructor.

**Assertion pseudocode:**
```
registry = ProviderRegistry()
registry.register("custom-", mock_constructor)
provider = registry.resolve("custom-model")
ASSERT provider is mock_constructor.return_value
```

---

### TS-12-24: Config supports all required keys

**Requirement:** 12-REQ-4.2
**Type:** unit
**Description:** Verify `CoderConfig` supports `model`, `templates_dir`,
`ollama_url`, `log_level`, and `log_file` keys with correct defaults.

**Preconditions:**
- Temporary `.coder.yaml` with all keys specified.

**Input:**
- Create `.coder.yaml` with: `model: test-model`, `templates_dir: /tmp/tpl`,
  `ollama_url: http://localhost:9999`, `log_level: INFO`,
  `log_file: /tmp/log.txt`.
- Call `load_config(project_dir=tmp_dir)`.

**Expected:**
- `config.model == "test-model"`
- `config.templates_dir == "/tmp/tpl"`
- `config.ollama_url == "http://localhost:9999"`
- `config.log_level == "INFO"`
- `config.log_file == "/tmp/log.txt"`

**Assertion pseudocode:**
```
yaml_content = """
model: test-model
templates_dir: /tmp/tpl
ollama_url: http://localhost:9999
log_level: INFO
log_file: /tmp/log.txt
"""
write_file(tmp_dir / ".coder.yaml", yaml_content)
config = load_config(project_dir=tmp_dir)
ASSERT config.model == "test-model"
ASSERT config.templates_dir == "/tmp/tpl"
ASSERT config.ollama_url == "http://localhost:9999"
ASSERT config.log_level == "INFO"
ASSERT config.log_file == "/tmp/log.txt"
```

---

### TS-12-25: Env var overrides use CODER_ prefix

**Requirement:** 12-REQ-4.3
**Type:** unit
**Description:** Verify environment variable overrides use the `CODER_` prefix
for each configuration key.

**Preconditions:**
- Empty temporary directory (no config file).
- Environment variables set: `CODER_OLLAMA_URL=http://custom:1234`,
  `CODER_LOG_LEVEL=WARNING`.

**Input:**
- Call `load_config(project_dir=tmp_dir)`.

**Expected:**
- `config.ollama_url == "http://custom:1234"`
- `config.log_level == "WARNING"`

**Assertion pseudocode:**
```
set_env("CODER_OLLAMA_URL", "http://custom:1234")
set_env("CODER_LOG_LEVEL", "WARNING")
config = load_config(project_dir=empty_tmp_dir)
ASSERT config.ollama_url == "http://custom:1234"
ASSERT config.log_level == "WARNING"
```

---

### TS-12-26: Config returns frozen pydantic model

**Requirement:** 12-REQ-4.5
**Type:** unit
**Description:** Verify `load_config()` returns a frozen pydantic `CoderConfig`
that validates types at load time.

**Preconditions:**
- Temporary `.coder.yaml` with `model: test-model`.

**Input:**
- Call `load_config(project_dir=tmp_dir)`.
- Attempt to mutate a field on the result.

**Expected:**
- Returns an instance of `CoderConfig` (pydantic model).
- Mutation raises a `ValidationError` or `TypeError` (frozen model).

**Assertion pseudocode:**
```
config = load_config(project_dir=tmp_dir)
ASSERT isinstance(config, CoderConfig)
ASSERT_RAISES (ValidationError or TypeError or AttributeError):
    config.model = "other-model"
```

---

### TS-12-27: assemble_prompt accepts persona, context, and variables

**Requirement:** 12-REQ-6.4
**Type:** unit
**Description:** Verify `assemble_prompt` accepts persona name, task context
string, and an optional variables dictionary, and returns the assembled prompt.

**Preconditions:**
- Templates: `agent.md` = "Base $project", `coder.md` = "Persona".

**Input:**
- `PromptAssembler.assemble(persona="coder", task_context="Context",
  variables={"project": "TestProject"})`.

**Expected:**
- Returns a string containing the substituted base, persona, and context.
- The result contains `"TestProject"` (from variable substitution).

**Assertion pseudocode:**
```
assembler = PromptAssembler(loader)
result = assembler.assemble(persona="coder", task_context="Context",
                            variables={"project": "TestProject"})
ASSERT "TestProject" in result
ASSERT "Persona" in result
ASSERT "Context" in result
```

---

### TS-12-28: CLI run accepts campaign_dir, --model, and --repo

**Requirement:** 12-REQ-7.2
**Type:** integration
**Description:** Verify `coder run` accepts all documented arguments:
`campaign_dir` (required), `--model` (optional), `--repo` (optional).

**Preconditions:**
- Temporary campaign directory exists.
- Provider `invoke` mocked to prevent API calls.

**Input:**
- Invoke `coder run <tmp_campaign_dir> --model claude-opus-4-6 --repo /tmp/repo`.

**Expected:**
- Exit code 0.
- All arguments are accepted without error.

**Assertion pseudocode:**
```
result = cli_runner.invoke(["run", str(tmp_campaign_dir),
                            "--model", "claude-opus-4-6",
                            "--repo", "/tmp/repo"])
ASSERT result.exit_code == 0
```

---

### TS-12-29: CLI models subcommand lists providers

**Requirement:** 12-REQ-7.4
**Type:** integration
**Description:** Verify `coder models` lists known model name prefixes and
their associated providers in a formatted table.

**Preconditions:**
- None.

**Input:**
- Invoke `coder models`.

**Expected:**
- Exit code 0.
- Output contains `claude-`, `gemini-`, and `ollama` (or equivalent).
- Output is formatted as a table.

**Assertion pseudocode:**
```
result = cli_runner.invoke(["models"])
ASSERT result.exit_code == 0
ASSERT "claude-" in result.output
ASSERT "gemini-" in result.output
```

---

### TS-12-30: CLI run --help displays usage

**Requirement:** 12-REQ-7.5
**Type:** integration
**Description:** Verify `coder run --help` displays usage information for all
arguments and options.

**Preconditions:**
- None.

**Input:**
- Invoke `coder run --help`.

**Expected:**
- Exit code 0.
- Output contains `campaign_dir`, `--model`, and `--repo`.

**Assertion pseudocode:**
```
result = cli_runner.invoke(["run", "--help"])
ASSERT result.exit_code == 0
ASSERT "campaign_dir" in result.output or "CAMPAIGN_DIR" in result.output
ASSERT "--model" in result.output
ASSERT "--repo" in result.output
```

---

### TS-12-31: Logging defaults to DEBUG level

**Requirement:** 12-REQ-8.2
**Type:** unit
**Description:** Verify the logging system defaults to DEBUG level when no
override is configured.

**Preconditions:**
- Default configuration (no config file, no env vars).

**Input:**
- Set up logging with default config, emit a DEBUG event.

**Expected:**
- DEBUG-level log events appear in output.

**Assertion pseudocode:**
```
config = load_config(project_dir=empty_tmp_dir)
ASSERT config.log_level == "DEBUG"
setup_logging(config)
logger = get_logger("test")
logger.debug("debug_event")
-- verify output contains "debug_event"
```

---

### TS-12-32: Logging writes to file when configured

**Requirement:** 12-REQ-8.3
**Type:** unit
**Description:** Verify log output is written to a file when `log_file` is
configured.

**Preconditions:**
- Temporary directory with writable log file path.

**Input:**
- Configure with `log_file` pointing to a temporary path.
- Emit a log event.

**Expected:**
- The log file exists and contains the emitted event.

**Assertion pseudocode:**
```
log_path = tmp_dir / "coder.log"
config = CoderConfig(log_file=str(log_path))
setup_logging(config)
logger = get_logger("test")
logger.info("file_event")
ASSERT log_path.exists()
ASSERT "file_event" in log_path.read_text()
```

---

### TS-12-33: get_logger returns bound logger with module name

**Requirement:** 12-REQ-8.5
**Type:** unit
**Description:** Verify `get_logger(name)` returns a structlog logger bound
with the given module name.

**Preconditions:**
- Logging has been set up.

**Input:**
- Call `get_logger("my_module")`.

**Expected:**
- Returns a bound logger.
- Log output from this logger includes `"my_module"` as the module context.

**Assertion pseudocode:**
```
setup_logging(config)
logger = get_logger("my_module")
logger.info("test_event")
-- verify output contains "my_module"
```

---

## Edge Case Tests

### TS-12-E12: API key missing raises ProviderConfigError

**Requirement:** 12-REQ-2.E2
**Type:** unit
**Description:** Verify missing API key for Anthropic/Google raises ProviderConfigError.

**Preconditions:**
- `ANTHROPIC_API_KEY` unset.

**Input:**
- `AnthropicProvider("claude-opus-4-6")`.

**Expected:**
- Raises `ProviderConfigError` naming `ANTHROPIC_API_KEY`.

**Assertion pseudocode:**
```
unset_env("ANTHROPIC_API_KEY")
ASSERT_RAISES ProviderConfigError:
    AnthropicProvider("claude-opus-4-6")
```

---

### TS-12-E13: Extra variables key ignored

**Requirement:** 12-REQ-6.E1
**Type:** unit
**Description:** Verify extra keys in variables dict do not cause errors.

**Preconditions:**
- Template with no `$extra` placeholder.

**Input:**
- `assemble(persona="coder", task_context="Ctx", variables={"extra": "val"})`.

**Expected:**
- No error raised.

**Assertion pseudocode:**
```
result = assembler.assemble("coder", "Ctx", variables={"extra": "val"})
ASSERT "Ctx" in result
```

---

### TS-12-E14: Campaign dir does not exist

**Requirement:** 12-REQ-7.E1
**Type:** integration
**Description:** Verify CLI exits with error for missing campaign directory.

**Preconditions:**
- None.

**Input:**
- `coder run /nonexistent/path`.

**Expected:**
- Exit code 1 with error message.

**Assertion pseudocode:**
```
result = cli_runner.invoke(["run", "/nonexistent/path"])
ASSERT result.exit_code == 1
```

---

### TS-12-E1: Ollama server unreachable

**Requirement:** 12-REQ-2.E1
**Type:** unit
**Description:** Verify clear error when Ollama is not running.

**Preconditions:**
- Ollama URL set to a non-listening port.

**Input:**
- Create `OllamaProvider("codestral:latest")` and call `validate()`.

**Expected:**
- Raises `ProviderConnectionError` with URL details.

**Assertion pseudocode:**
```
provider = OllamaProvider("codestral:latest", ollama_url="http://localhost:99999")
ASSERT_RAISES ProviderConnectionError:
    provider.validate()
```

---

### TS-12-E2: Empty model name rejected

**Requirement:** 12-REQ-3.E1
**Type:** unit
**Description:** Verify registry rejects empty model name.

**Preconditions:**
- None.

**Input:**
- `ProviderRegistry().resolve("")`.

**Expected:**
- Raises `ValueError`.

**Assertion pseudocode:**
```
ASSERT_RAISES ValueError:
    ProviderRegistry().resolve("")
```

---

### TS-12-E3: No config file uses defaults

**Requirement:** 12-REQ-4.E2
**Type:** unit
**Description:** Verify defaults are used when no config file exists.

**Preconditions:**
- Empty temporary directory with no `.coder.yaml`.

**Input:**
- `load_config(project_dir=tmp_dir)`.

**Expected:**
- Returns valid `CoderConfig` with default values.

**Assertion pseudocode:**
```
config = load_config(project_dir=empty_tmp_dir)
ASSERT config.ollama_url == "http://localhost:11434"
ASSERT config.log_level == "DEBUG"
```

---

### TS-12-E4: Invalid YAML raises ConfigError

**Requirement:** 12-REQ-4.E3
**Type:** unit
**Description:** Verify malformed YAML is caught.

**Preconditions:**
- `.coder.yaml` with invalid content: `model: [unclosed`.

**Input:**
- `load_config(project_dir=tmp_dir)`.

**Expected:**
- Raises `ConfigError`.

**Assertion pseudocode:**
```
write_file(tmp_dir / ".coder.yaml", "model: [unclosed")
ASSERT_RAISES ConfigError:
    load_config(project_dir=tmp_dir)
```

---

### TS-12-E5: Template not found raises TemplateNotFoundError

**Requirement:** 12-REQ-5.E1
**Type:** unit
**Description:** Verify missing template produces a clear error.

**Preconditions:**
- No template named `nonexistent` in any search path.

**Input:**
- `TemplateLoader().load("nonexistent")`.

**Expected:**
- Raises `TemplateNotFoundError` listing searched paths.

**Assertion pseudocode:**
```
ASSERT_RAISES TemplateNotFoundError:
    TemplateLoader().load("nonexistent")
```

---

### TS-12-E6: Symlink template rejected

**Requirement:** 12-REQ-5.5
**Type:** unit
**Description:** Verify symlinks in template directory are rejected.

**Preconditions:**
- Template directory contains a symlink `evil.md` → `/etc/passwd`.

**Input:**
- `TemplateLoader(project_dir=tmp_dir).load("evil")`.

**Expected:**
- Raises `TemplateSecurityError`.

**Assertion pseudocode:**
```
create_symlink(tmp_dir / ".coder/templates/evil.md", "/etc/passwd")
ASSERT_RAISES TemplateSecurityError:
    TemplateLoader(project_dir=tmp_dir).load("evil")
```

---

### TS-12-E7: Unknown YAML keys logged as warnings

**Requirement:** 12-REQ-4.E1
**Type:** unit
**Description:** Verify unknown config keys are warned about.

**Preconditions:**
- `.coder.yaml` with `model: test\nunknown_key: value`.

**Input:**
- `load_config(project_dir=tmp_dir)`.

**Expected:**
- Config loads successfully. A warning is logged for `unknown_key`.

**Assertion pseudocode:**
```
write_file(tmp_dir / ".coder.yaml", "model: test\nunknown_key: value\n")
with capture_logs() as logs:
    config = load_config(project_dir=tmp_dir)
ASSERT config.model == "test"
ASSERT any("unknown_key" in log for log in logs)
```

### TS-12-E8: Build system error if coder directory already exists

**Requirement:** 12-REQ-1.E1
**Type:** unit
**Description:** Verify the build system raises an error during `uv sync`
rather than silently overwriting if `packages/coder/` already exists with
conflicting content.

**Preconditions:**
- `packages/coder/` exists with a `pyproject.toml` that conflicts with
  the expected package definition.

**Input:**
- Attempt `uv sync` or equivalent workspace resolution.

**Expected:**
- Build system raises an error rather than silently overwriting.

**Assertion pseudocode:**
```
-- This is a build-system-level constraint verified by workspace tooling.
-- The test verifies that uv sync detects the conflict:
ASSERT_RAISES BuildError:
    run_command("uv sync")
-- OR verify via pyproject.toml parsing that the workspace member is
-- correctly declared (no duplicate/conflicting entries).
```

---

### TS-12-E9: Empty template file returns empty string

**Requirement:** 12-REQ-5.E2
**Type:** unit
**Description:** Verify loading a zero-byte template file returns an empty
string without error.

**Preconditions:**
- Template file `empty.md` exists but has zero bytes.

**Input:**
- `TemplateLoader(project_dir=tmp_dir).load("empty")`.

**Expected:**
- Returns `""` (empty string) without raising an error.

**Assertion pseudocode:**
```
write_file(tmp_dir / ".coder/templates/empty.md", "")
loader = TemplateLoader(project_dir=tmp_dir)
content = loader.load("empty")
ASSERT content == ""
```

---

### TS-12-E10: CLI prints provider error on creation failure

**Requirement:** 12-REQ-7.E2
**Type:** integration
**Description:** Verify `coder run` prints the provider error to stderr and
exits with code 1 when the `--model` argument specifies a provider that
cannot be created (e.g., missing API key).

**Preconditions:**
- `ANTHROPIC_API_KEY` is unset.
- Temporary campaign directory exists.

**Input:**
- Invoke `coder run <tmp_campaign_dir> --model claude-opus-4-6`.

**Expected:**
- Exit code 1.
- Stderr contains an error message about the provider or API key.

**Assertion pseudocode:**
```
unset_env("ANTHROPIC_API_KEY")
result = cli_runner.invoke(["run", str(tmp_campaign_dir), "--model", "claude-opus-4-6"])
ASSERT result.exit_code == 1
ASSERT "ANTHROPIC_API_KEY" in result.output or "provider" in result.output.lower()
```

---

### TS-12-E11: Unwritable log file falls back to console

**Requirement:** 12-REQ-8.E1
**Type:** unit
**Description:** Verify that when the log file path is not writable, the
system logs a warning to stderr and continues with console-only logging.

**Preconditions:**
- `log_file` set to an unwritable path (e.g., `/nonexistent/dir/coder.log`).

**Input:**
- Set up logging with the unwritable `log_file` path.
- Emit a log event.

**Expected:**
- No exception raised during setup.
- A warning about the unwritable log file is emitted to stderr.
- Console logging continues to work normally.

**Assertion pseudocode:**
```
config = CoderConfig(log_file="/nonexistent/dir/coder.log")
setup_logging(config)  -- should not raise
logger = get_logger("test")
logger.info("fallback_event")
-- verify stderr contains warning about log file
-- verify console output still contains "fallback_event"
```

---

## Integration Smoke Tests

### TS-12-SMOKE-1: CLI run resolves provider

**Execution Path:** Path 1 from design.md
**Description:** Verify the full CLI invocation path from command to
provider resolution.

**Setup:** Temporary campaign directory exists. `ANTHROPIC_API_KEY` set to
a test value. Provider `invoke` method is mocked to prevent actual API calls.

**Trigger:** `coder run <campaign_dir> --model claude-opus-4-6`

**Expected side effects:**
- Exit code 0.
- Log output contains model name `claude-opus-4-6`.
- Provider instance created is `AnthropicProvider`.

**Must NOT satisfy with:** Mocking `ProviderRegistry.resolve` — the real
resolution must execute.

**Assertion pseudocode:**
```
result = cli_runner.invoke(["run", str(campaign_dir), "--model", "claude-opus-4-6"])
ASSERT result.exit_code == 0
ASSERT "claude-opus-4-6" in captured_logs
```

---

### TS-12-SMOKE-2: Prompt assembly end-to-end

**Execution Path:** Path 2 from design.md
**Description:** Verify prompt assembly loads real templates and composes
them correctly.

**Setup:** Package default templates exist on disk.

**Trigger:** `PromptAssembler.assemble(persona="coder", task_context="Implement X")`

**Expected side effects:**
- Returns a string containing content from `agent.md`, `coder.md`, and
  `"Implement X"` in order.

**Must NOT satisfy with:** Mocking `TemplateLoader.load` — real filesystem
reads must execute.

**Assertion pseudocode:**
```
assembler = PromptAssembler(TemplateLoader())
result = assembler.assemble(persona="coder", task_context="Implement X")
ASSERT "Implement X" in result
ASSERT len(result) > len("Implement X")  -- other layers present
```

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 12-REQ-1.1 | TS-12-1 | unit |
| 12-REQ-1.2 | TS-12-2 | unit |
| 12-REQ-2.2 | TS-12-3 | unit |
| 12-REQ-2.3 | TS-12-4 | unit |
| 12-REQ-2.4 | TS-12-5 | unit |
| 12-REQ-2.5 | TS-12-6 | unit |
| 12-REQ-2.E1 | TS-12-E1 | unit |
| 12-REQ-2.E2 | TS-12-6 | unit |
| 12-REQ-3.2 | TS-12-7 | unit |
| 12-REQ-3.3 | TS-12-8 | unit |
| 12-REQ-3.4 | TS-12-9 | unit |
| 12-REQ-3.E1 | TS-12-E2 | unit |
| 12-REQ-4.1 | TS-12-10 | unit |
| 12-REQ-4.4 | TS-12-11 | unit |
| 12-REQ-4.E1 | TS-12-E7 | unit |
| 12-REQ-4.E2 | TS-12-E3 | unit |
| 12-REQ-4.E3 | TS-12-E4 | unit |
| 12-REQ-5.1 | TS-12-12 | unit |
| 12-REQ-5.2 | TS-12-13 | unit |
| 12-REQ-5.3 | TS-12-14 | unit |
| 12-REQ-5.4 | TS-12-P3 | property |
| 12-REQ-5.5 | TS-12-E6 | unit |
| 12-REQ-5.6 | TS-12-12 | unit |
| 12-REQ-5.E1 | TS-12-E5 | unit |
| 12-REQ-6.1 | TS-12-15 | unit |
| 12-REQ-6.2 | TS-12-16 | unit |
| 12-REQ-6.3 | TS-12-P5 | property |
| 12-REQ-6.E1 | TS-12-P5 | property |
| 12-REQ-7.1 | TS-12-17 | integration |
| 12-REQ-7.3 | TS-12-17 | integration |
| 12-REQ-7.E1 | TS-12-18 | integration |
| 12-REQ-8.1 | TS-12-19 | unit |
| 12-REQ-8.4 | TS-12-19 | unit |
| Property 1 | TS-12-P1 | property |
| Property 2 | TS-12-P2 | property |
| Property 3 | TS-12-P3 | property |
| Property 4 | TS-12-P4 | property |
| Property 5 | TS-12-P5 | property |
| Path 1 | TS-12-SMOKE-1 | integration |
| Path 2 | TS-12-SMOKE-2 | integration |
| 12-REQ-1.3 | TS-12-20 | unit |
| 12-REQ-1.E1 | TS-12-E8 | unit |
| 12-REQ-2.1 | TS-12-21 | unit |
| 12-REQ-3.1 | TS-12-22 | unit |
| 12-REQ-3.5 | TS-12-23 | unit |
| 12-REQ-4.2 | TS-12-24 | unit |
| 12-REQ-4.3 | TS-12-25 | unit |
| 12-REQ-4.5 | TS-12-26 | unit |
| 12-REQ-5.E2 | TS-12-E9 | unit |
| 12-REQ-6.4 | TS-12-27 | unit |
| 12-REQ-7.2 | TS-12-28 | integration |
| 12-REQ-7.4 | TS-12-29 | integration |
| 12-REQ-7.5 | TS-12-30 | integration |
| 12-REQ-7.E2 | TS-12-E10 | integration |
| 12-REQ-8.2 | TS-12-31 | unit |
| 12-REQ-8.3 | TS-12-32 | unit |
| 12-REQ-8.5 | TS-12-33 | unit |
| 12-REQ-8.E1 | TS-12-E11 | unit |

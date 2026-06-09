# speclib

The spec creation tool for standalone authoring of spec packages.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (required package manager)

## Installation

Install speclib using uv:

```bash
uv pip install .
```

For development:

```bash
uv sync
```

## Usage

```bash
af-spec --help
```

## Development

Run the full quality suite:

```bash
make check
```

Run tests only:

```bash
make test
```

## Configuration

speclib reads configuration from `~/.af/settings.yaml`. Environment variables
override settings file values:

| Variable | Purpose |
|----------|---------|
| `AF_SPEC_MODEL` | Model name |
| `AF_SPEC_AUTH` | Auth method (`api_key`, `bedrock`, `vertex`) |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `AF_SPEC_VERTEX_PROJECT` | GCP project (for Vertex auth) |
| `AF_SPEC_VERTEX_REGION` | GCP region (for Vertex auth) |

# Contributing to OANP

Thanks for your interest in contributing. Here's how to get started.

## Setup

```bash
git clone https://github.com/cemphlvn/OANP.git
cd OANP
cp .env.example .env          # Add your LLM API key
npm run setup:all              # Install all dependencies
```

## Development

```bash
# Run a simulation
python simulate.py scenarios/salary-negotiation.yaml

# Start the web UI (frontend + backend)
npm run dev

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/
```

## Adding a Scenario

1. Copy an existing scenario: `cp scenarios/salary-negotiation.yaml scenarios/my-scenario.yaml`
2. Edit the YAML — define parties, interests, BATNAs, issues, and criteria
3. Test it: `python simulate.py scenarios/my-scenario.yaml`
4. Submit a PR

Scenario quality checklist:
- At least 2 parties with 3+ interests each
- BATNAs defined for all parties (with realistic utility scores)
- 3-5 issues with clear options or ranges
- At least 2 objective criteria
- Interests should have varied priorities (not all 0.9)

## Code Style

- Python: formatted with [ruff](https://docs.astral.sh/ruff/), line length 100
- No unused imports, no `print()` for logging (use `logging` module)
- Type annotations on public functions
- Tests for new functionality

## Pull Requests

- Keep PRs focused — one feature or fix per PR
- Include a test if you're changing behavior
- Run `uv run pytest tests/ -v` and `uv run ruff check src/` before submitting

## Architecture Overview

```
src/
├── protocol/     # Core types — no LLM deps, pure Pydantic models
├── agents/       # LLM-powered agents (negotiator, mediator, analyst, scorer)
├── ontology/     # Graphiti knowledge graph (optional, requires Neo4j)
└── backend/      # FastAPI server + WebSocket
```

Key design decisions:
- **Shared/private state split** — agents only see their own private state + shared domain
- **Typed moves** — every negotiation action is a `Move` with a `MoveType` enum
- **Information boundaries** — `StateView` enforces what each actor can see
- **LLM scorer** — utility is measured by LLM judgment grounded in satisfaction anchors, not hardcoded math

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

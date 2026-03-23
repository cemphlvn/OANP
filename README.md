<div align="center">

# OANP

**Ontology-based Agentic Negotiation Protocol**

Principled multi-party negotiation, formalized as an open protocol.

<a href="https://github.com/cemphlvn/OANP/blob/main/LICENSE">
  <img src="https://img.shields.io/github/license/cemphlvn/OANP?style=flat" />
</a>
<a href="https://github.com/cemphlvn/OANP/actions">
  <img src="https://img.shields.io/github/actions/workflow/status/cemphlvn/OANP/ci.yml?style=flat&label=tests" />
</a>
<a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white" />
</a>

<br />
<br />

<a href="#quick-start">Quick Start</a> ·
<a href="scenarios/">Scenarios</a> ·
<a href="paper/oanp-one-pager.md">Paper</a> ·
<a href="CONTRIBUTING.md">Contributing</a>

</div>

<br />

OANP is an open protocol and simulation framework for multi-party negotiation using autonomous agents. Agents negotiate using [Harvard Negotiation Project](https://www.pon.harvard.edu/) principles, focusing on interests rather than positions, formalized through domain ontologies.

> **Define** parties, interests, BATNAs, and issues in a YAML file.
> OANP **runs** a principled negotiation with autonomous agents, streams moves in real time, and delivers a settlement or analysis of why agreement was not reached.

<br />

<table>
<tr>
<td width="50%" valign="top">

### For Researchers

Typed protocol with 10 move types, 9 negotiation phases, configurable mediator architectures (facilitative / evaluative / arbitrative), and full metrics: Pareto efficiency, Nash product, integrative index, BATNA surplus.

</td>
<td width="50%" valign="top">

### For Practitioners

12 built-in scenarios from salary negotiation to the Iran nuclear deal. Define any domain in YAML. Plug in OpenAI, Anthropic, or any compatible endpoint. MIT licensed.

</td>
</tr>
</table>

## Why OANP

- **Interest-first** &mdash; agents reason about *why* parties want things, not just *what* they demand
- **BATNA-safe** &mdash; no party accepts a deal worse than their best alternative
- **Integrative** &mdash; the protocol incentivizes expanding the pie, not splitting it
- **Observable** &mdash; every move is typed, timestamped, traceable
- **Ontology-grounded** &mdash; shared semantic representation, not prompt engineering

> [!NOTE]
> OANP's approach is validated by the [MIT AI Negotiation Competition](https://arxiv.org/abs/2503.06416) (2025, ~180,000 negotiations) which found that agents adhering to Harvard principles consistently outperform positional bargaining agents.

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/cemphlvn/OANP.git && cd OANP
cp .env.example .env        # add your OpenAI or Anthropic API key

# 2. Install
npm run setup:all            # installs Node + Python deps

# 3. Run a negotiation
python simulate.py scenarios/salary-negotiation.yaml
```

<details>
<summary><strong>More options</strong></summary>

<br />

```bash
# Use a specific model
python simulate.py scenarios/salary-negotiation.yaml --model claude-sonnet-4-6

# JSON output for analysis
python simulate.py scenarios/salary-negotiation.yaml --output json --out-file results/run.json

# Generate a scenario from natural language
python simulate.py --generate "Two co-founders splitting equity after one wants to leave"

# Interactive scenario builder
python simulate.py --create

# Start the web UI (frontend + backend)
npm run dev
```

| Service | URL |
|---------|-----|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8123` |
| API Docs | `http://localhost:8123/docs` |

</details>

## Scenarios

OANP ships with 12 scenarios spanning employment, commercial, legal, and geopolitical domains:

| Scenario | Domain | Parties |
|----------|--------|---------|
| [Salary Negotiation](scenarios/salary-negotiation.yaml) | Employment | Candidate vs Employer |
| [Landlord-Tenant](scenarios/landlord-tenant.yaml) | Dispute Resolution | Tenant vs Landlord |
| [B2B SaaS Contract](scenarios/b2b-saas-contract.yaml) | Commercial | Buyer vs Vendor |
| [Custody Dispute](scenarios/custody-bitter-divorce.yaml) | Family Law | Mother vs Father |
| [Union Strike](scenarios/union-strike-deadlock.yaml) | Labor | Union vs Hospital |
| [Pharma Patent](scenarios/pharma-patent-dying-patients.yaml) | Healthcare | Biotech vs Patient Advocacy |
| [Startup Acquisition](scenarios/startup-acquisition.yaml) | M&A | Founder vs BigTech |
| [AI Safety: Ship or Stop](scenarios/ai-safety-release.yaml) | Governance | Safety Lead vs Product Lead |
| [US-China Trade](scenarios/us-china-trade.yaml) | Geopolitics | US Trade Rep vs China Commerce |
| [1998 NBA Lockout](scenarios/nba-lockout-1998.yaml) | Sports Labor | NBA Owners vs Players |
| [Apple vs Samsung](scenarios/apple-samsung-patent.yaml) | IP Litigation | Apple CEO vs Samsung CEO |
| [Iran Nuclear Deal](scenarios/iran-nuclear-2015.yaml) | Diplomacy | US (P5+1) vs Iran |

```bash
# Create your own
cp scenarios/salary-negotiation.yaml scenarios/my-scenario.yaml
```

## How It Works

```
Scenario (YAML)
    |
    v
┌─────────────────────────────────────────────┐
│  Discovery → Generation → Bargaining → ...  │  9 phases
│                                             │
│  Negotiator ←→ Mediator ←→ Negotiator      │  typed moves
│       |              |            |          │
│   [private]     [configurable]  [private]   │  information boundaries
│    state        knowledge level   state     │
└─────────────────────────────────────────────┘
    |
    v
Settlement + Metrics (utility, Pareto, Nash, integrative index)
```

<details>
<summary><strong>Architecture details</strong></summary>

<br />

**Protocol types** (`src/protocol/types.py`) define the formal type system: `NegotiationState`, `Move`, `Interest`, `BATNA`, `OptionPackage`, `ObjectiveCriterion`. This is the single source of truth.

**Agents** (`src/agents/`) are LLM-powered:
- `negotiator.py` &mdash; party agent with Harvard principles encoded in the system prompt, theory-of-mind before each move
- `mediator.py` &mdash; configurable neutral facilitator (facilitative / evaluative / arbitrative)
- `scorer.py` &mdash; LLM utility scorer with satisfaction anchors and pairwise BATNA comparison
- `analyst.py` &mdash; post-hoc metrics (social welfare, Pareto efficiency, Nash product, integrative index)
- `validator.py` &mdash; structural safety layer preventing illegal moves and BATNA violations

**Information boundaries** (`src/protocol/views.py`) enforce what each actor can see. This is structural, not a prompt instruction.

**Engine** (`src/agents/graph.py`) orchestrates negotiation as a LangGraph state machine with Command-based routing.

```
OANP/
├── simulate.py              # CLI runner
├── scenarios/               # YAML negotiation scenarios
├── paper/                   # Research paper
├── tests/                   # Test suite
└── src/
    ├── protocol/            # Core types, scenario loader, state views
    ├── agents/              # Negotiator, mediator, scorer, analyst, engine
    ├── ontology/            # Graphiti knowledge graph (optional)
    └── backend/             # FastAPI + WebSocket server
```

</details>

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, WebSocket |
| **Agents** | LangGraph, LangChain |
| **Memory** | Graphiti + Neo4j (optional) |
| **LLMs** | OpenAI, Anthropic, or any OpenAI-compatible endpoint |
| **Frontend** | Vue 3, Vite, D3.js |

> [!TIP]
> All code dependencies are MIT or Apache 2.0. You need an LLM API key to run negotiations.

## Research

OANP is grounded in research across automated negotiation, legal informatics, and multi-agent systems. See the [paper](paper/oanp-one-pager.md) for full positioning and references.

Key influences:
- Fisher & Ury, *Getting to Yes* (1981) &mdash; principled negotiation
- Rahwan et al. (2003) &mdash; interest-based negotiation in multi-agent systems
- MIT AI Negotiation Competition (2025) &mdash; empirical validation at 180K negotiations
- Singapore Convention on Mediation (2019) &mdash; cross-border enforceability

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Key areas: new scenarios, agent strategies, ontology templates, frontend.

## License

MIT &mdash; see [LICENSE](LICENSE).

---

<div align="center">
<sub>Built by <a href="mailto:cem@talp.ai">Cem Pehlivan</a></sub>
</div>

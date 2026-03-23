"""
Natural Language → Scenario Generator

"I want to simulate a divorce mediation over custody and asset splitting"
  → generates a full YAML scenario with parties, interests, BATNAs, issues, criteria

This is the zero-friction entry point. No YAML writing needed.

Usage:
    python simulate.py --generate "two cofounders splitting equity after one wants to leave"
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel


class GeneratedParty(BaseModel):
    id: str = Field(description="Short snake_case identifier")
    name: str = Field(description="Display name with role in parentheses")
    role: str = Field(description="Role in the negotiation")
    interests: list[dict] = Field(
        description="List of interests, each with: description (str), type (need/desire/fear/concern), "
        "priority (0.0-1.0), related_issues (list of issue IDs)"
    )
    batna: dict = Field(
        description="BATNA with: description (str), utility (0.0-1.0), "
        "confidence (0.0-1.0), components (dict of issue_id -> value)"
    )


class GeneratedScenario(BaseModel):
    name: str = Field(description="Descriptive scenario name")
    description: str = Field(description="One-line description of the negotiation")
    architecture: str = Field(description="bilateral or mediated")
    parties: list[GeneratedParty]
    issues: list[dict] = Field(
        description="List of issues, each with: id (str), name (str), type (monetary/categorical/temporal), "
        "and either options (list of str) or range (list of two numbers), and divisible (bool)"
    )
    criteria: list[dict] = Field(
        description="List of objective criteria, each with: name (str), source (str), "
        "applies_to (list of issue IDs), reference_value (str)"
    )
    mediator: dict = Field(
        default_factory=lambda: {
            "mode": "facilitative",
            "knowledge": "caucus_only",
            "intervention": "every_round",
            "evaluates_fairness": False,
        },
        description="Mediator configuration"
    )


GENERATOR_PROMPT = """You are an expert negotiation scenario designer for the OANP \
(Ontology-based Agentic Negotiation Protocol) simulation system.

Given a natural language description of a negotiation situation, generate a complete, \
realistic scenario. Think deeply about the DYNAMICS of this specific negotiation before \
generating — don't just fill in a template.

## Step 1: Analyze the Situation

Before generating, reason about:

**Domain**: What kind of negotiation is this?
- Commercial (contract, procurement, partnership)
- Employment (salary, terms, severance)
- Dispute resolution (landlord-tenant, neighbor, consumer)
- Legal/family (custody, divorce, inheritance)
- International/political (trade, treaty, alliance)

**Power dynamics**: Who has more leverage and why?
- Whose BATNA is stronger? (The party with better alternatives has more power)
- Who is more time-pressured? (Urgency weakens bargaining position)
- Who has more information? (Information asymmetry creates leverage)
- Is there a power imbalance to model? (employer vs employee, landlord vs tenant)

**Emotional landscape**: What emotions drive this negotiation?
- Is there trust or distrust between parties? Why?
- Is there a relationship at stake beyond this deal?
- Are there identity/dignity concerns? (being treated fairly, saving face)
- What are each party's deepest fears about this negotiation?

**Integrative potential**: Where can value be CREATED, not just divided?
- Which issues do parties value DIFFERENTLY? (Trade-off levers)
- Are there creative options neither party has considered?
- Can issues be linked or sequenced to unlock value?

## Step 2: Design the Scenario

**Parties** (2-4):
- Give them realistic names, specific roles, and clear motivations
- Design LAYERED interests for each party:
  - Surface interests (what they say they want)
  - Underlying needs (why they want it — security, recognition, flexibility, control)
  - Fears (what they're afraid of if the negotiation fails or goes badly)
  - Concerns (worries about the process or the other party)
- Assign priorities (0.0-1.0) that reflect the RELATIVE importance — not all high
- Design ASYMMETRIC BATNAs:
  - One party should have a stronger alternative than the other
  - BATNAs should be SPECIFIC (not "walk away" but "file lawsuit in small claims court" \
    or "accept the competing offer from CompanyX at $150K")
  - Include a utility score (0.0-1.0) reflecting how good the BATNA actually is
  - Include a confidence score — how certain is the party their BATNA will work?

**Issues** (3-6):
- Mix types: monetary (salary, price, rent), categorical (options, policies), temporal (dates, durations)
- Design for COMPLEMENTARY VALUATIONS: Party A cares most about Issue X, Party B cares \
  most about Issue Y — this creates trade-off potential
- Include at least one issue that seems important but could be conceded cheaply
- Include at least one creative option that neither party would initially think of

**Objective Criteria** (2-4):
- Domain-appropriate: market rates, legal standards, industry norms, precedents, regulations
- Include at least one criterion that favors each party — criteria shouldn't all point one way
- Be specific with reference values (not "market rate" but "$140K-$165K per Levels.fyi")

**Architecture**:
- Mediated for: disputes, multi-party, emotional situations, power imbalance
- Bilateral for: straightforward commercial deals between equals

## What Makes a GREAT Scenario

A great scenario is one where:
- The outcome is NOT obvious — multiple reasonable deals are possible
- Both parties have legitimate interests that partially conflict
- Creative solutions exist that neither party would propose without exploration
- The power balance is unequal but not overwhelming
- Emotions and relationships matter, not just economics
- A mediator (if present) can genuinely help by surfacing hidden value"""


async def generate_scenario(description: str, llm: BaseChatModel) -> dict:
    """Generate a scenario from natural language description. Returns YAML-ready dict."""

    structured_llm = llm.with_structured_output(GeneratedScenario)

    response: GeneratedScenario = await structured_llm.ainvoke([
        SystemMessage(content=GENERATOR_PROMPT),
        HumanMessage(content=f"""Generate a negotiation scenario for:

"{description}"

First analyze: what domain is this? Who has power? What emotions are at play? \
Where is the integrative potential? Then generate the scenario with layered interests, \
asymmetric BATNAs, and complementary issue valuations."""),
    ])

    # Convert to YAML-compatible dict
    scenario = {
        "name": response.name,
        "description": response.description,
        "architecture": response.architecture,
        "parties": [p.model_dump() for p in response.parties],
        "issues": response.issues,
        "criteria": response.criteria,
        "mediator": response.mediator,
        "protocol": {
            "max_rounds": 20,
            "disclosure_policy": "gradual",
        },
    }

    return scenario

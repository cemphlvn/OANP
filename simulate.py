"""
OANP CLI Simulation Runner

Usage:
    # Human-readable output (pretty terminal)
    python simulate.py scenarios/salary-negotiation.yaml

    # Machine-readable output (JSON to file — for the observe-criticize-improve loop)
    python simulate.py scenarios/salary-negotiation.yaml --output json --out-file results/run_001.json

    # Quick iteration with cheaper model
    python simulate.py scenarios/salary-negotiation.yaml --model gpt-4o-mini --output json --out-file results/run_001.json

    # Verbose mode
    python simulate.py scenarios/salary-negotiation.yaml -v

The --output json mode produces a structured result file containing:
  1. Full move history with all details
  2. Computed metrics (utility, Pareto, Nash, integrative index)
  3. A self-critique section identifying issues with agent behavior
  4. Metadata (model, scenario, timing)

This structure enables the observe-criticize-learn-improve loop:
  Run → Read JSON → Identify issues → Edit code → Run again
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from src.protocol.scenario import load_scenario
from src.protocol.types import NegotiationState, MoveType
from src.agents.graph import NegotiationEngine
from src.agents.analyst import analyze_negotiation, analyze_negotiation_llm, format_metrics_report, NegotiationMetrics


# ---------------------------------------------------------------------------
# Self-critique — evaluates negotiation quality against Harvard principles
# ---------------------------------------------------------------------------

def critique_negotiation(state: NegotiationState, metrics: NegotiationMetrics) -> list[dict]:
    """
    Automated critique of the negotiation. Returns a list of issues found.

    Each issue has:
      - category: what aspect is problematic
      - severity: "high" | "medium" | "low"
      - description: what went wrong
      - suggestion: how to fix it in the code/prompts

    This is the "criticize" step of the loop. Claude Code reads these
    and decides what to improve.
    """
    issues = []

    # --- Outcome quality ---
    if metrics.outcome == "impasse":
        # Check if BATNA surplus was possible (ZOPA existed)
        total_batna = sum(
            (state.private_states[p.id].batna.utility
             if state.private_states.get(p.id) and state.private_states[p.id].batna else 0)
            for p in state.parties
        )
        if total_batna < len(state.parties) * 0.7:
            issues.append({
                "category": "outcome",
                "severity": "high",
                "description": "Negotiation ended in impasse despite likely ZOPA. "
                               "Agents failed to find an agreement zone.",
                "suggestion": "Improve negotiator prompts to be more concession-willing. "
                              "Check if mediator is generating creative packages.",
            })

    # --- Harvard Principle: Focus on interests ---
    disclosure_moves = [m for m in state.move_history if m.move_type == MoveType.DISCLOSE_INTEREST]
    if len(disclosure_moves) == 0:
        issues.append({
            "category": "harvard_interests",
            "severity": "high",
            "description": "No interests were disclosed during the negotiation. "
                           "Agents went straight to positional bargaining.",
            "suggestion": "The discovery phase may be too short or agents aren't choosing "
                          "DISCLOSE_INTEREST moves. Check get_legal_moves() and negotiator prompt.",
        })
    elif metrics.disclosure_rate < 0.2:
        issues.append({
            "category": "harvard_interests",
            "severity": "medium",
            "description": f"Low disclosure rate ({metrics.disclosure_rate:.0%}). "
                           "Agents are withholding interests.",
            "suggestion": "Adjust disclosure_policy or cooperation_level in strategy. "
                          "The negotiator prompt should encourage gradual disclosure.",
        })

    # --- Harvard Principle: Generate options for mutual gain ---
    meso_moves = [m for m in state.move_history if m.move_type == MoveType.MESO]
    proposals = [m for m in state.move_history if m.move_type in (MoveType.PROPOSE, MoveType.COUNTER)]
    if len(meso_moves) == 0 and len(proposals) < 3:
        issues.append({
            "category": "harvard_options",
            "severity": "medium",
            "description": "Few proposals and no MESO moves. Agents aren't generating "
                           "creative options for mutual gain.",
            "suggestion": "Generation phase may be too short. Consider having the mediator "
                          "generate MESOs. Check if generation_node transitions too quickly.",
        })

    # --- Harvard Principle: Objective criteria ---
    criterion_moves = [m for m in state.move_history if m.move_type == MoveType.INVOKE_CRITERION]
    # Criteria invocation by negotiators is always encouraged
    # Mediator invoking criteria depends on mode (evaluative/arbitrative only)
    if len(criterion_moves) == 0 and len(state.criteria) > 0:
        mediator_mode = state.mediator.config.mode.value if state.mediator else "none"
        suggestion = "Add criteria context to the negotiator prompt more prominently."
        if mediator_mode in ("evaluative", "arbitrative"):
            suggestion += " The mediator is in evaluative mode — it should reference criteria."
        issues.append({
            "category": "harvard_criteria",
            "severity": "medium",
            "description": f"Objective criteria defined ({len(state.criteria)}) but never invoked. "
                           "Agents are negotiating without anchoring to fair standards.",
            "suggestion": suggestion,
        })

    # --- Harvard Principle: BATNA awareness ---
    for party in state.parties:
        ps = state.private_states.get(party.id)
        if not ps or not ps.batna:
            continue
        utility = metrics.party_utilities.get(party.id, 0)
        if utility < ps.batna.utility and metrics.outcome == "agreement":
            issues.append({
                "category": "batna_violation",
                "severity": "high",
                "description": f"{party.name} accepted a deal (utility={utility:.2f}) worse than "
                               f"their BATNA (utility={ps.batna.utility:.2f}). This should never happen.",
                "suggestion": "The negotiator agent must compare proposed packages against BATNA "
                              "before accepting. Add explicit BATNA check in the acceptance logic.",
            })

    # --- Move quality ---
    if metrics.total_moves < 4:
        issues.append({
            "category": "process",
            "severity": "medium",
            "description": f"Very few moves ({metrics.total_moves}). Negotiation may have "
                           "short-circuited without real bargaining.",
            "suggestion": "Check phase transition logic — are phases ending too early? "
                          "Should_transition functions may have thresholds too low.",
        })

    argue_moves = [m for m in state.move_history if m.move_type == MoveType.ARGUE]
    if len(argue_moves) == 0 and metrics.total_moves > 5:
        issues.append({
            "category": "argumentation",
            "severity": "low",
            "description": "No argumentation moves. Agents are only exchanging proposals "
                           "without justification.",
            "suggestion": "Encourage ARGUE moves in the negotiator prompt. Arguments "
                          "unlock deals that pure offer-exchange cannot (ABN literature).",
        })

    # --- Integrative quality ---
    if metrics.integrative_index < 1.0 and metrics.outcome == "agreement":
        issues.append({
            "category": "integrative",
            "severity": "medium",
            "description": f"Integrative index {metrics.integrative_index:.2f} < 1.0. "
                           "The negotiation destroyed value relative to BATNAs.",
            "suggestion": "The mediator should be finding interest overlaps and trade-offs. "
                          "Check if discovery phase is surfacing enough interests.",
        })

    # --- Outcome asymmetry (observation, not a bug) ---
    if metrics.outcome == "agreement":
        surpluses = list(metrics.party_batna_surplus.values())
        if surpluses and max(surpluses) > 3 * max(min(surpluses), 0.01):
            issues.append({
                "category": "observation_asymmetry",
                "severity": "info",
                "description": "Asymmetric outcome — one party captured more surplus. "
                               "This is an observation, not necessarily a problem. "
                               "A facilitative mediator does not balance outcomes.",
                "suggestion": "Compare with evaluative mediator mode to see if criteria "
                              "anchoring produces more symmetric results. This is a research question.",
            })

    # --- Parse failures ---
    # Check for moves without packages when they should have them
    for move in state.move_history:
        if move.move_type in (MoveType.PROPOSE, MoveType.COUNTER, MoveType.MESO) and not move.package:
            issues.append({
                "category": "parse_error",
                "severity": "high",
                "description": f"Move {move.id} is {move.move_type.value} but has no package. "
                               "LLM output parsing likely failed.",
                "suggestion": "Check negotiator.py run_negotiator() JSON parsing. "
                              "The LLM may not be returning the expected format.",
            })
            break  # only report once

    return issues


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def build_json_result(
    state: NegotiationState,
    metrics: NegotiationMetrics,
    critique: list[dict],
    metadata: dict,
) -> dict:
    """Build the full structured JSON result for the observe-criticize loop."""
    return {
        "metadata": metadata,
        "outcome": {
            "result": metrics.outcome,
            "rounds": metrics.total_rounds,
            "total_moves": metrics.total_moves,
            "agreement": metrics.agreement,
        },
        "metrics": {
            "party_utilities": metrics.party_utilities,
            "party_batna_surplus": metrics.party_batna_surplus,
            "party_interest_satisfaction": metrics.party_interest_satisfaction,
            "social_welfare": metrics.social_welfare,
            "pareto_efficient": metrics.pareto_efficient,
            "nash_product": metrics.nash_product,
            "integrative_index": metrics.integrative_index,
            "disclosure_rate": metrics.disclosure_rate,
            "move_breakdown": metrics.move_breakdown,
        },
        "critique": {
            "issues": critique,
            "issue_count": len(critique),
            "high_severity": len([i for i in critique if i["severity"] == "high"]),
            "medium_severity": len([i for i in critique if i["severity"] == "medium"]),
            "low_severity": len([i for i in critique if i["severity"] == "low"]),
            "info": len([i for i in critique if i["severity"] == "info"]),
        },
        "move_history": [
            {
                "id": m.id,
                "timestamp": m.timestamp.isoformat(),
                "party_id": m.party_id,
                "move_type": m.move_type.value,
                "phase": m.phase,
                "round": m.round,
                "turn": m.turn,
                "package": m.package.model_dump() if m.package else None,
                "argument": m.argument.model_dump() if m.argument else None,
                "references": m.references,
            }
            for m in state.move_history
        ],
        "parties": [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role,
            }
            for p in state.parties
        ],
        # Legal compliance (advanced mode)
        "compliance": {
            "mode": state.compliance.mode.value,
            "institution": state.compliance.institution.framework.value if state.compliance.institution else None,
            "procedure": state.compliance.institution.procedure if state.compliance.institution else None,
            "seat": state.compliance.institution.seat if state.compliance.institution else None,
            "governing_law": state.compliance.institution.governing_law if state.compliance.institution else None,
            "current_tier": state.compliance.current_tier.value,
            "tier_history": state.compliance.tier_history,
            "escalation_tiers": [t.value for t in state.compliance.escalation.tiers] if state.compliance.escalation else [],
        } if state.compliance else None,
        "award": state.award.model_dump(mode="json") if state.award else None,
    }


# ---------------------------------------------------------------------------
# Terminal output (pretty mode)
# ---------------------------------------------------------------------------

COLORS = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
    "blue": "\033[94m", "magenta": "\033[95m", "cyan": "\033[96m",
}

def c(text: str, color: str) -> str:
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"

PARTY_COLORS = ["blue", "magenta", "cyan", "yellow", "green"]
MOVE_ICONS = {
    "propose": "📋", "counter": "↩️ ", "argue": "💬",
    "disclose_interest": "🔓", "invoke_criterion": "⚖️ ",
    "accept": "✅", "reject": "❌", "invoke_batna": "🚪", "meso": "📦",
}
PHASE_COLORS = {
    "discovery": "cyan", "generation": "magenta", "bargaining": "yellow",
    "convergence": "blue", "settlement": "green", "impasse": "red",
}


def print_event(event_type: str, data: dict, verbose: bool = False):
    if event_type == "phase_change":
        phase = data.get("phase", "")
        col = PHASE_COLORS.get(phase, "dim")
        print(f"\n{c('═' * 60, col)}")
        print(f"  {c(f'Phase: {phase.upper()}', col)}  |  Round {data.get('round', '?')}")
        if data.get("message"):
            print(f"  {c(data['message'], 'dim')}")
        print(f"{c('═' * 60, col)}\n")

    elif event_type == "move":
        party = data.get("party_name", "?")
        mt = data.get("move_type", "?")
        pidx = hash(party) % len(PARTY_COLORS)
        icon = MOVE_ICONS.get(mt, "•")
        print(f"  {icon} {c(party, PARTY_COLORS[pidx])}: {c(mt, 'bold')}")
        if data.get("package"):
            for k, v in data["package"].get("issue_values", {}).items():
                print(f"      {c(k, 'dim')}: {v}")
            if data["package"].get("rationale"):
                print(f"      {c('rationale:', 'dim')} {data['package']['rationale']}")
        if data.get("argument") and data["argument"].get("claim"):
            print(f"      {c('claim:', 'dim')} \"{data['argument']['claim']}\"")

    elif event_type == "anchors_generated":
        print(f"  {c('⚓', 'cyan')} {c(data.get('party_name', '?'), 'cyan')}: "
              f"{data.get('anchor_count', 0)} satisfaction anchors generated")

    elif event_type == "anchors_failed":
        print(f"  {c('⚠️', 'yellow')} Anchor generation failed for "
              f"{data.get('party_id', '?')}: {data.get('error', '?')}")

    elif event_type == "mediator_note":
        print(f"\n  {c('🤝 MEDIATOR', 'green')}: ", end="")
        if data.get("package"):
            print(f"{c('suggests package', 'bold')}")
            for k, v in data["package"].get("issue_values", {}).items():
                print(f"      {c(k, 'dim')}: {v}")
        elif data.get("argument"):
            print(f"{c(data['argument'].get('claim', ''), 'bold')}")
        print()

    elif event_type == "settlement":
        print(f"\n{c('🎉 SETTLEMENT REACHED', 'green')}")
        print(f"   Rounds: {data.get('total_rounds', data.get('rounds', '?'))}  |  Moves: {data.get('total_moves', '?')}")
        if data.get("agreement"):
            print(f"\n   {c('Final Agreement:', 'bold')}")
            for k, v in data["agreement"].get("issue_values", {}).items():
                print(f"      {c(k, 'dim')}: {c(str(v), 'green')}")
        if data.get("award"):
            award = data["award"]
            print(f"\n   {c('Award:', 'bold')}")
            print(f"      Type:      {c(award.get('award_type', '?').replace('_', ' ').upper(), 'cyan')}")
            if award.get("seat"):
                print(f"      Seat:      {award['seat']}")
            if award.get("governing_law"):
                print(f"      Law:       {award['governing_law']}")
            if award.get("institution"):
                print(f"      Framework: {award['institution'].upper()}")
            if award.get("integrity_hash"):
                print(f"      Hash:      {c(award['integrity_hash'][:24] + '...', 'dim')}")

    elif event_type == "impasse":
        print(f"\n{c('❌ IMPASSE', 'red')}")
        print(f"   Rounds: {data.get('rounds', '?')}  |  Moves: {data.get('total_moves', '?')}")


# ---------------------------------------------------------------------------
# LLM initialization
# ---------------------------------------------------------------------------

def get_llm(model: str):
    if model.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, temperature=0.7, max_tokens=4096)
    elif model.startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, temperature=0.7, max_output_tokens=4096)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0.7, max_tokens=4096)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="OANP Negotiation Simulator",
        epilog="The --output json mode enables the observe-criticize-improve loop."
    )
    parser.add_argument("scenario", nargs="?", help="Path to scenario YAML file")
    parser.add_argument("--generate", "-g", type=str, default=None,
                        help="Generate scenario from natural language (single-shot)")
    parser.add_argument("--create", action="store_true",
                        help="Interactive scenario builder — asks clarifying questions")
    parser.add_argument("--model", default=os.getenv("OANP_DEFAULT_MODEL", "gpt-4o"),
                        help="LLM model (default: gpt-4o)")
    parser.add_argument("--output", choices=["pretty", "json"], default="pretty",
                        help="Output format (default: pretty)")
    parser.add_argument("--out-file", help="Write JSON results to file (requires --output json)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.generate:
        # Generate scenario from natural language
        from src.protocol.generate import generate_scenario
        import yaml

        llm = get_llm(args.model)
        print(f"Generating scenario from: \"{args.generate}\"...", file=sys.stderr)
        scenario_dict = await generate_scenario(args.generate, llm)

        # Save generated scenario
        gen_path = Path(f"scenarios/generated-{scenario_dict.get('name', 'scenario').lower().replace(' ', '-')[:40]}.yaml")
        gen_path.parent.mkdir(exist_ok=True)
        with open(gen_path, "w") as f:
            yaml.dump(scenario_dict, f, default_flow_style=False, sort_keys=False)
        print(f"Scenario saved to: {gen_path}", file=sys.stderr)

        state = load_scenario(gen_path)
        scenario_path = gen_path

    elif args.create:
        # Interactive specification agent — multi-turn conversation
        from src.protocol.specify import SpecificationAgent

        llm = get_llm(args.model)
        agent = SpecificationAgent(llm)

        print(f"\n{c('OANP Scenario Builder', 'bold')}")
        print(f"{c('─' * 40, 'dim')}")
        print(f"  Describe your negotiation and I'll ask clarifying questions.")
        print(f"  Type {c('done', 'cyan')} to generate with what we have.\n")

        initial = input(f"  {c('You:', 'cyan')} ")
        step = await agent.step(initial)

        while step.type == "question":
            # Show what's known
            if step.known:
                known_items = []
                for k, v in step.known.items():
                    if v:
                        known_items.append(f"{k}")
                if known_items:
                    print(f"\n  {c('Known:', 'green')} {', '.join(known_items)}")
            if step.missing:
                print(f"  {c('Missing:', 'yellow')} {', '.join(step.missing[:4])}")
            print(f"  {c('Confidence:', 'dim')} {step.confidence:.0%}")

            print(f"\n  {c('🤖:', 'magenta')} {step.question}\n")

            answer = input(f"  {c('You:', 'cyan')} ")
            if answer.strip().lower() in ("done", "generate", "go", ""):
                break
            step = await agent.step(answer)

        print(f"\n  {c('Generating scenario...', 'dim')}")
        import yaml
        scenario_dict = await agent.generate()

        gen_path = Path(f"scenarios/generated-{scenario_dict.get('name', 'scenario').lower().replace(' ', '-')[:40]}.yaml")
        gen_path.parent.mkdir(exist_ok=True)
        with open(gen_path, "w") as f:
            yaml.dump(scenario_dict, f, default_flow_style=False, sort_keys=False)

        state = load_scenario(gen_path)
        scenario_path = gen_path

        # Show what was generated
        print(f"\n  {c('✅ Scenario generated:', 'green')} {scenario_dict.get('name', '?')}")
        print(f"  Parties: {', '.join(p.name for p in state.parties)}")
        print(f"  Issues:  {', '.join(i.name for i in state.issues)}")
        print(f"  Saved:   {gen_path}")
        print(f"{c('─' * 40, 'dim')}\n")

    elif args.scenario:
        scenario_path = Path(args.scenario)
        if not scenario_path.exists():
            print(f"Error: Scenario not found: {scenario_path}", file=sys.stderr)
            sys.exit(1)
        state = load_scenario(scenario_path)
    else:
        print("Error: provide a scenario file or use --generate", file=sys.stderr)
        sys.exit(1)

    # Metadata for the result file
    metadata = {
        "scenario": str(scenario_path),
        "model": args.model,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "parties": [p.name for p in state.parties],
        "issues": [i.name for i in state.issues],
        "architecture": state.protocol.architecture.value,
    }

    if args.output == "pretty":
        print(f"\n{c('OANP Negotiation Simulator', 'bold')}")
        print(f"{c('─' * 40, 'dim')}")
        print(f"  Scenario: {c(scenario_path.stem, 'cyan')}")
        print(f"  Model:    {c(args.model, 'cyan')}")
        print(f"  Parties:  {', '.join(p.name for p in state.parties)}")
        print(f"  Issues:   {', '.join(i.name for i in state.issues)}")
        if state.compliance and state.compliance.mode.value == "advanced":
            inst = state.compliance.institution
            esc = state.compliance.escalation
            dl = state.compliance.deadlines
            print(f"  {c('Mode:', 'yellow')}    {c('ADVANCED (Formal Procedure)', 'yellow')}")
            if inst:
                print(f"  Rules:    {c(inst.framework.value.upper(), 'cyan')} {inst.procedure}")
                if inst.seat:
                    print(f"  Seat:     {inst.seat}")
                if inst.governing_law:
                    print(f"  Law:      {inst.governing_law}")
            if esc:
                tiers = ' → '.join(t.value.upper() for t in esc.tiers)
                print(f"  Tiers:    {tiers}")
            if dl and dl.hard_deadline_rounds:
                print(f"  Deadline: {dl.hard_deadline_rounds} rounds (hard limit)")
        print(f"{c('─' * 40, 'dim')}")

    # Initialize LLM
    llm = get_llm(args.model)

    # Run
    start_time = time.time()

    if args.output == "pretty":
        on_event = lambda t, d: print_event(t, d, args.verbose)
    else:
        on_event = lambda t, d: None  # silent in JSON mode

    engine = NegotiationEngine(state=state, llm=llm, on_event=on_event)

    try:
        final_state = await engine.run()
    except KeyboardInterrupt:
        print(f"\nInterrupted.", file=sys.stderr)
        sys.exit(0)

    elapsed = time.time() - start_time
    metadata["elapsed_seconds"] = round(elapsed, 2)

    # Analyze — use LLM scorer for accurate utility measurement
    metrics = await analyze_negotiation_llm(final_state, engine.scorer)
    critique = critique_negotiation(final_state, metrics)

    if args.output == "pretty":
        # Print metrics report
        print(format_metrics_report(metrics, final_state))

        # Print compliance summary (advanced mode)
        if final_state.compliance and final_state.compliance.mode.value == "advanced":
            print(f"\n{c('COMPLIANCE', 'cyan')}")
            print(f"  Institution: {final_state.compliance.institution.framework.value.upper() if final_state.compliance.institution else 'N/A'}")
            print(f"  Final tier:  {final_state.compliance.current_tier.value.upper()}")
            tier_h = final_state.compliance.tier_history
            if tier_h:
                print(f"  Escalations: {len(tier_h)}")
                for th in tier_h:
                    print(f"    Round {th['at_round']}: {th['from_tier']} → {th['to_tier']} ({th['reason']})")
            else:
                print(f"  Escalations: None (resolved at initial tier)")

            from src.protocol.compliance import ComplianceEngine
            ce = ComplianceEngine(final_state.compliance)
            violations = ce.validate_due_process(final_state)
            print(f"  Due process: {c('No violations', 'green') if not violations else c(str(len(violations)) + ' issues', 'red')}")

            if final_state.award:
                print(f"  Award:       {final_state.award.award_type.value.replace('_', ' ').upper()}")
                print(f"  Hash:        {final_state.award.integrity_hash[:24]}...")

        # Print critique
        if critique:
            print(f"\n{c('CRITIQUE', 'yellow')} ({len(critique)} issues found):")
            for issue in critique:
                sev_color = {"high": "red", "medium": "yellow", "low": "dim", "info": "cyan"}.get(issue["severity"], "dim")
                print(f"  [{c(issue['severity'].upper(), sev_color)}] "
                      f"{c(issue['category'], 'bold')}: {issue['description']}")

    elif args.output == "json":
        result = build_json_result(final_state, metrics, critique, metadata)

        if args.out_file:
            out_path = Path(args.out_file)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"Results written to {out_path}", file=sys.stderr)
        else:
            print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

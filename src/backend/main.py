"""
OANP Backend — FastAPI server with WebSocket for real-time negotiation streaming.

Architecture:
- FastAPI serves REST API + WebSocket endpoints
- LangGraph manages the negotiation state machine
- WebSocket streams moves, phase transitions, and mediator notes to frontend
- Human-in-the-loop: frontend sends moves via WebSocket when it's a human party's turn
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..protocol.types import NegotiationState
from ..agents.cache import SessionStore

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="OANP — Ontology-based Agentic Negotiation Protocol",
    version="0.1.0",
    description="Multi-agent negotiation engine using Harvard negotiation principles",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("OANP_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# In-memory session store (swap for Redis/Postgres in production)
# ---------------------------------------------------------------------------

store = SessionStore(data_dir="results")



# ---------------------------------------------------------------------------
# REST API — session and scenario management
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "oanp", "version": "0.1.0"}


@app.get("/api/stats")
async def get_stats():
    """Basic stats for the landing page counter."""
    return {"sessions_total": store.count + len(_demo_cache)}


class CreateSessionRequest(BaseModel):
    scenario_path: str | None = None
    # Advanced mode config (all optional — backward compatible)
    mode: str | None = None  # "streamlined" | "advanced"
    institution: dict | None = None  # {framework, procedure, seat, governing_law, ...}
    escalation: dict | None = None  # {tiers, negotiation_deadline_rounds, ...}
    deadlines: dict | None = None  # {phase_max_rounds, hard_deadline_rounds, ...}


@app.post("/api/sessions")
async def create_session(body: CreateSessionRequest = CreateSessionRequest()):
    """Create a new negotiation session, optionally from a scenario file."""
    if body.scenario_path:
        from ..protocol.scenario import load_scenario, load_scenario_from_dict
        from pathlib import Path
        import yaml

        scenario_path = Path(body.scenario_path)
        # Resolve stem-only paths (e.g. "salary-negotiation") to full path
        if not scenario_path.exists():
            scenarios_dir = Path(__file__).parent.parent.parent / "scenarios"
            resolved = scenarios_dir / f"{scenario_path.stem}.yaml"
            if resolved.exists():
                scenario_path = resolved
            else:
                # Try as-is with .yaml extension
                alt = scenarios_dir / f"{body.scenario_path}.yaml"
                if alt.exists():
                    scenario_path = alt

        # If advanced mode config provided, merge it into the scenario
        if body.mode == "advanced" or body.institution:
            with open(scenario_path) as f:
                raw = yaml.safe_load(f)
            raw["mode"] = body.mode or "advanced"
            if body.institution:
                raw["institution"] = body.institution
            if body.escalation:
                raw["escalation"] = body.escalation
            if body.deadlines:
                raw["deadlines"] = body.deadlines
            state = load_scenario_from_dict(raw)
        else:
            state = load_scenario(str(scenario_path))
    else:
        state = NegotiationState()

    store.put(state)

    return {
        "session_id": state.id,
        "parties": [p.model_dump() for p in state.parties],
        "issues": [i.model_dump() for i in state.issues],
        "phase": state.protocol.phase.value,
        "architecture": state.protocol.architecture.value,
        "compliance": state.compliance.mode.value if state.compliance else None,
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get the shared (public) state of a negotiation session."""
    from ..protocol.views import StateView

    state = store.get(session_id)
    if state:
        return StateView.for_frontend(state)

    # Fall back to demo cache
    if session_id in _demo_cache:
        demo = _demo_cache[session_id]
        return {
            "session_id": session_id,
            "parties": demo.get("parties", []),
            "issues": demo.get("issues", []),
            "criteria": demo.get("criteria", []),
            "outcome": demo.get("outcome"),
            "agreement": demo.get("agreement"),
        }

    return {"error": "Session not found"}


@app.get("/api/sessions/{session_id}/moves")
async def get_moves(session_id: str):
    """Get the move history for a session."""
    state = store.get(session_id)
    if state:
        return {"moves": [m.model_dump() for m in state.move_history]}

    # Fall back to demo cache — extract moves from events
    if session_id in _demo_cache:
        demo = _demo_cache[session_id]
        moves = [e["data"] for e in demo.get("events", []) if e["type"] in ("move", "mediator_note")]
        return {"moves": moves}

    return {"error": "Session not found"}


@app.get("/api/scenarios")
async def list_scenarios():
    """List available scenario templates."""
    from pathlib import Path

    scenarios_dir = Path(__file__).parent.parent.parent / "scenarios"
    if not scenarios_dir.exists():
        return {"scenarios": []}

    scenarios = []
    for f in scenarios_dir.glob("*.yaml"):
        import yaml
        with open(f) as fh:
            raw = yaml.safe_load(fh)
        scenarios.append({
            "name": raw.get("name", f.stem),
            "description": raw.get("description", ""),
            "file": f.stem,
            "parties": len(raw.get("parties", [])),
            "issues": len(raw.get("issues", [])),
        })

    return {"scenarios": scenarios}


class GenerateRequest(BaseModel):
    prompt: str


class SpecifyRequest(BaseModel):
    session_id: str | None = None
    message: str


# Active specification sessions (conversation state)
spec_sessions: dict[str, object] = {}  # SpecificationAgent instances


@app.post("/api/specify")
async def specify_step(body: SpecifyRequest):
    """Multi-turn scenario specification. Returns question or ready signal."""
    try:
        return await _specify_step_inner(body)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


async def _specify_step_inner(body: SpecifyRequest):
    from ..protocol.specify import SpecificationAgent

    # Get or create spec session
    if body.session_id and body.session_id in spec_sessions:
        agent = spec_sessions[body.session_id]
    else:
        llm = get_default_llm()
        agent = SpecificationAgent(llm)
        sid = f"spec_{uuid.uuid4().hex[:8]}"
        spec_sessions[sid] = agent
        body.session_id = sid

    step = await agent.step(body.message)

    result = {
        "session_id": body.session_id,
        "type": step.type,
        "question": step.question,
        "known": step.known,
        "missing": step.missing,
        "confidence": step.confidence,
        "turn": agent.turn_count,
    }

    # If ready, generate the scenario
    if step.type == "ready" or step.confidence >= 0.8:
        from ..protocol.scenario import load_scenario_from_dict

        scenario_dict = await agent.generate()
        state = load_scenario_from_dict(scenario_dict)
        store.put(state)

        result["type"] = "ready"
        result["negotiation_session_id"] = state.id
        result["scenario"] = {
            "name": scenario_dict.get("name", ""),
            "parties": [p.model_dump() for p in state.parties],
            "issues": [i.model_dump() for i in state.issues],
        }

        # Clean up spec session
        del spec_sessions[body.session_id]

    return result


def get_default_llm(max_tokens: int = 4096):
    """Initialize the default LLM from env config."""
    model_name = os.getenv("OANP_DEFAULT_MODEL", "gpt-4o")
    if model_name.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, temperature=0.7, max_tokens=max_tokens)
    elif model_name.startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, temperature=0.7, max_output_tokens=max_tokens)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, temperature=0.7, max_tokens=max_tokens)


@app.post("/api/generate")
async def generate_from_nl(body: GenerateRequest):
    """Generate a scenario from natural language and create a session."""
    from ..protocol.generate import generate_scenario
    from ..protocol.scenario import load_scenario_from_dict

    try:
        llm = get_default_llm()
        scenario_dict = await generate_scenario(body.prompt, llm)
        state = load_scenario_from_dict(scenario_dict)
        store.put(state)

        return {
            "session_id": state.id,
            "scenario": scenario_dict,
            "parties": [p.model_dump() for p in state.parties],
            "issues": [i.model_dump() for i in state.issues],
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def _save_event_stream(session_id: str, events: list[dict], state):
    """Save the full event stream for demo replay."""
    from pathlib import Path
    from ..agents.analyst import analyze_negotiation
    from ..protocol.views import StateView

    demo_dir = Path(__file__).parent.parent.parent / "demos"
    demo_dir.mkdir(exist_ok=True)

    # Compute timing delays between events
    timed_events = []
    for i, event in enumerate(events):
        delay_ms = 0
        if i > 0:
            try:
                from datetime import datetime
                t1 = datetime.fromisoformat(events[i-1]["timestamp"])
                t2 = datetime.fromisoformat(event["timestamp"])
                delay_ms = int((t2 - t1).total_seconds() * 1000)
                # Cap delays: min 200ms, max 4000ms for demo pacing
                delay_ms = max(200, min(4000, delay_ms))
            except Exception:
                delay_ms = 500
        timed_events.append({
            "type": event["type"],
            "data": event["data"],
            "delay_ms": delay_ms,
        })

    # Compute metrics
    metrics = analyze_negotiation(state)
    critique = _critique(state, metrics)

    # Build the demo package
    frontend_state = StateView.for_frontend(state)
    demo = {
        "session_id": session_id,
        "scenario_name": state.parties[0].name + " vs " + state.parties[1].name if len(state.parties) >= 2 else "Demo",
        "description": f"{len(state.parties)} parties, {len(state.issues)} issues, {metrics.outcome}",
        "parties": frontend_state["parties"],
        "issues": frontend_state["issues"],
        "criteria": [c.model_dump(mode="json") for c in state.criteria],
        "outcome": metrics.outcome,
        "agreement": frontend_state.get("agreement"),
        "events": timed_events,
        "metrics": {
            "outcome": metrics.outcome,
            "party_utilities": metrics.party_utilities,
            "party_batna_surplus": metrics.party_batna_surplus,
            "social_welfare": metrics.social_welfare,
            "pareto_efficient": metrics.pareto_efficient,
            "nash_product": metrics.nash_product,
            "integrative_index": metrics.integrative_index,
            "total_rounds": metrics.total_rounds,
            "total_moves": metrics.total_moves,
            "move_breakdown": metrics.move_breakdown,
            "disclosure_rate": metrics.disclosure_rate,
            "phases_visited": metrics.phases_visited,
            "agreement": frontend_state.get("agreement"),
        },
        "critique": critique,
    }

    path = demo_dir / f"{session_id}.json"
    try:
        with open(path, "w") as f:
            json.dump(demo, f, indent=2, default=str)
        logger.info("Saved event stream: %s (%d events)", path, len(timed_events))
    except Exception as e:
        logger.error("Demo save failed: %s", e)


def _critique(state, metrics):
    """Quick critique of negotiation quality."""
    from ..protocol.types import MoveType
    issues = []
    if metrics.outcome == "impasse":
        issues.append({"severity": "high", "description": "Negotiation ended in impasse — no agreement reached."})
    if metrics.disclosure_rate < 0.3:
        issues.append({"severity": "medium", "description": f"Low disclosure rate ({metrics.disclosure_rate:.0%}) — agents withheld interests."})
    meso = sum(1 for m in state.move_history if m.move_type == MoveType.MESO)
    if meso == 0:
        issues.append({"severity": "low", "description": "No multi-option (MESO) packages were generated."})
    crit = sum(1 for m in state.move_history if m.move_type == MoveType.INVOKE_CRITERION)
    if crit == 0:
        issues.append({"severity": "low", "description": "Objective criteria were never invoked."})
    if metrics.integrative_index is not None and metrics.integrative_index < 1.0:
        issues.append({"severity": "medium", "description": f"Integrative index {metrics.integrative_index:.2f} < 1.0 — value may have been destroyed."})
    if metrics.integrative_index is not None and metrics.integrative_index >= 1.2:
        issues.append({"severity": "info", "description": f"Integrative index {metrics.integrative_index:.2f} — negotiation created significant value."})
    if metrics.pareto_efficient:
        issues.append({"severity": "info", "description": "Agreement is Pareto efficient."})
    return issues


@app.get("/api/sessions/{session_id}/analysis")
async def get_analysis(session_id: str):
    """Get post-negotiation metrics and analysis."""
    # Check demo cache — demos have pre-computed metrics
    if session_id in _demo_cache:
        demo = _demo_cache[session_id]
        if demo.get("metrics"):
            # Extract BCI opponent models from belief_update events
            opponent_models = {}
            for event in demo.get("events", []):
                if event.get("type") == "belief_update":
                    d = event["data"]
                    key = f"{d['observer_party_id']}→{d['target_party_id']}"
                    opponent_models[key] = d["belief"]
            return {
                **demo["metrics"],
                "critique": demo.get("critique", []),
                "opponent_models": opponent_models,
            }

    from ..agents.analyst import analyze_negotiation

    state = store.get(session_id)
    if not state:
        return {"error": "Session not found"}

    metrics = analyze_negotiation(state)
    critique = _critique(state, metrics)
    return {
        "outcome": metrics.outcome,
        "party_utilities": metrics.party_utilities,
        "party_batna_surplus": metrics.party_batna_surplus,
        "party_interest_satisfaction": metrics.party_interest_satisfaction,
        "social_welfare": metrics.social_welfare,
        "pareto_efficient": metrics.pareto_efficient,
        "nash_product": metrics.nash_product,
        "integrative_index": metrics.integrative_index,
        "total_rounds": metrics.total_rounds,
        "total_moves": metrics.total_moves,
        "move_breakdown": metrics.move_breakdown,
        "disclosure_rate": metrics.disclosure_rate,
        "phases_visited": metrics.phases_visited,
        "agreement": metrics.agreement,
        "critique": critique,
        "opponent_models": {
            f"{pid}→{tid}": belief.model_dump(mode="json") if hasattr(belief, "model_dump") else belief
            for pid, ps in state.private_states.items()
            for tid, belief in ps.belief_models.items()
        },
    }


# ---------------------------------------------------------------------------
# Institution Profiles API — legal compliance configuration
# ---------------------------------------------------------------------------

@app.get("/api/institutions")
async def list_institutions():
    """List all available institution profiles with summaries."""
    from ..protocol.institutions import list_profiles, get_profile_summary
    profiles = []
    for pid in list_profiles():
        try:
            profiles.append(get_profile_summary(pid))
        except Exception:
            pass
    return {"institutions": profiles}


@app.get("/api/institutions/{institution_id}")
async def get_institution(institution_id: str):
    """Get full institution profile."""
    from ..protocol.institutions import load_profile
    try:
        return load_profile(institution_id)
    except FileNotFoundError:
        return {"error": f"Institution '{institution_id}' not found"}


@app.get("/api/sessions/{session_id}/compliance")
async def get_compliance(session_id: str):
    """Get compliance metadata, checklists, and award for a session."""
    state = store.get(session_id)
    if not state:
        return {"error": "Session not found"}

    result = {"mode": "streamlined", "compliance": None, "award": None, "checklists": None}

    if state.compliance:
        from ..protocol.compliance import ComplianceEngine
        from ..protocol.award import format_award_text, format_compliance_report

        ce = ComplianceEngine(state.compliance)
        result["mode"] = state.compliance.mode.value
        result["compliance"] = {
            "current_tier": state.compliance.current_tier.value,
            "tier_history": state.compliance.tier_history,
            "due_process_log": state.compliance.due_process_log,
            "due_process_violations": ce.validate_due_process(state),
            "institution": state.compliance.institution.model_dump(mode="json") if state.compliance.institution else None,
            "escalation": state.compliance.escalation.model_dump(mode="json") if state.compliance.escalation else None,
            "deadlines": state.compliance.deadlines.model_dump(mode="json") if state.compliance.deadlines else None,
        }
        result["checklists"] = {
            "pre_negotiation": ce.get_pre_negotiation_checklist(),
            "during": ce.get_during_negotiation_checklist(state),
            "award": ce.get_award_checklist(),
        }

    if state.award:
        from ..protocol.award import format_award_text, format_compliance_report
        result["award"] = {
            **state.award.model_dump(mode="json"),
            "formatted_text": format_award_text(state.award, state),
            "compliance_report": format_compliance_report(state.award, state),
        }

    return result


# ---------------------------------------------------------------------------
# Demo / Replay API — pre-recorded negotiations for instant preview
# ---------------------------------------------------------------------------

# In-memory demo cache (loaded from demos/ dir on first access)
_demo_cache: dict[str, dict] = {}


def _load_demos():
    """Load all demo recordings from demos/ directory."""
    from pathlib import Path
    # Resolve relative to project root (parent of src/)
    demo_dir = Path(__file__).parent.parent.parent / "demos"
    if not demo_dir.exists():
        logger.debug("No demos directory at %s", demo_dir)
        return
    # Clear and reload fresh from disk
    _demo_cache.clear()
    for path in demo_dir.glob("*.json"):
        try:
            with open(path) as f:
                demo = json.load(f)
            _demo_cache[demo["session_id"]] = demo
        except Exception as e:
            logger.warning("Failed to load demo %s: %s", path, e)


@asynccontextmanager
async def _lifespan(app):
    _load_demos()
    yield

app.router.lifespan_context = _lifespan


@app.get("/api/demos")
async def list_demos():
    """List available demo recordings."""
    _load_demos()  # Always reload from disk
    demos = []
    for sid, demo in _demo_cache.items():
        demos.append({
            "session_id": sid,
            "scenario_name": demo.get("scenario_name", "Unknown"),
            "description": demo.get("description", ""),
            "outcome": demo.get("outcome"),
            "event_count": len(demo.get("events", [])),
            "parties": demo.get("parties", []),
            "issues": demo.get("issues", []),
        })
    return {"demos": demos}


@app.get("/api/demos/{session_id}")
async def get_demo(session_id: str):
    """Get a full demo recording for replay."""
    if session_id not in _demo_cache:
        return {"error": "Demo not found"}
    return _demo_cache[session_id]


# ---------------------------------------------------------------------------
# WebSocket — real-time negotiation streaming
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self.active:
            self.active[session_id] = []
        self.active[session_id].append(ws)

    def disconnect(self, session_id: str, ws: WebSocket):
        if session_id in self.active:
            self.active[session_id] = [
                w for w in self.active[session_id] if w != ws
            ]

    async def broadcast(self, session_id: str, event: dict):
        """Send an event to all clients watching this session."""
        for ws in self.active.get(session_id, []):
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.warning("Broadcast error: %s — event type: %s", e, event.get("type", "?"))


manager = ConnectionManager()


def make_event(event_type: str, data: dict) -> dict:
    return {
        "type": event_type,
        "data": data,
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for a negotiation session.

    Events sent TO client:
      - move: an agent made a move
      - phase_change: protocol phase transitioned
      - mediator_note: mediator intervention
      - turn_request: human player's turn (waiting for input)
      - settlement: agreement reached
      - impasse: no agreement
      - error: something went wrong

    Events received FROM client:
      - human_move: human player submitting their move
      - start: begin the negotiation simulation
    """
    await manager.connect(session_id, websocket)

    state = store.get(session_id)
    if not state:
        await websocket.send_json(make_event("error", {"message": "Session not found"}))
        await websocket.close()
        return

    # Send current state on connect
    await websocket.send_json(make_event("phase_change", {
        "phase": state.protocol.phase.value,
        "round": state.protocol.round,
        "parties": [p.model_dump() for p in state.parties],
    }))

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "start":
                # Apply config from frontend (if provided)
                cfg = data.get("config", {})
                if cfg and state.mediator:
                    from ..protocol.types import MediatorMode, MediatorKnowledge, MediatorIntervention, Architecture
                    if cfg.get("architecture") == "bilateral":
                        state.protocol.architecture = Architecture.BILATERAL
                        state.mediator = None
                    else:
                        state.protocol.architecture = Architecture.MEDIATED
                        if cfg.get("mediator_mode"):
                            state.mediator.config.mode = MediatorMode(cfg["mediator_mode"])
                        if cfg.get("mediator_knowledge"):
                            state.mediator.config.knowledge = MediatorKnowledge(cfg["mediator_knowledge"])
                        if cfg.get("mediator_intervention"):
                            state.mediator.config.intervention = MediatorIntervention(cfg["mediator_intervention"])

                # Run negotiation in background task
                import asyncio

                async def run_negotiation():
                    llm = get_default_llm()
                    from ..agents.graph import NegotiationEngine
                    from ..agents.events import EventBus

                    bus = EventBus()

                    async def _relay(event_type, data):
                        """Relay events from engine to all WebSocket clients."""
                        logger.debug("%s | %s: %s", session_id[:12], event_type, str(data)[:120])
                        await manager.broadcast(session_id, {"type": event_type, "data": data})

                    bus.subscribe(_relay)

                    engine = NegotiationEngine(
                        state=state, llm=llm, event_bus=bus,
                    )

                    try:
                        logger.info("Starting negotiation for %s", session_id)
                        await engine.run()
                        logger.info("Negotiation completed for %s", session_id)
                        # Checkpoint on completion
                        store.save(state)
                        # Save event stream for replay/demo
                        _save_event_stream(session_id, bus.history, state)
                    except Exception as e:
                        import traceback
                        error_msg = f"{type(e).__name__}: {e}"
                        logger.error("Negotiation error %s: %s", session_id, error_msg)
                        traceback.print_exc()
                        try:
                            await manager.broadcast(session_id, {
                                "type": "error",
                                "data": {"message": error_msg},
                            })
                        except Exception:
                            pass

                task = asyncio.create_task(run_negotiation())
                # Log if the task dies with an unhandled exception
                def _on_done(t):
                    if t.exception():
                        logger.critical("Engine crash %s: %s", session_id, t.exception())
                        import traceback
                        traceback.print_exception(type(t.exception()), t.exception(), t.exception().__traceback__)
                task.add_done_callback(_on_done)

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.backend.main:app",
        host=os.getenv("OANP_HOST", "0.0.0.0"),
        port=int(os.getenv("OANP_PORT", "8123")),
        reload=True,
    )

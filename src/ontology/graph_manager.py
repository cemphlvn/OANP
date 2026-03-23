"""
OANP Graph Manager — builds and updates the negotiation knowledge graph.

Architecture:
- Episodes are negotiation moves (proposals, arguments, disclosures) not social media posts
- The prescribed ontology is negotiation-specific (parties, interests, issues, packages)
- Bi-temporal tracking captures WHEN offers were made and WHEN they were superseded

Uses Graphiti (open source) directly, not Zep Cloud — keeping the project fully free.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..protocol.types import (
    Move,
    MoveType,
    NegotiationState,
)
from .graphiti_types import (
    NEGOTIATION_EDGE_TYPE_MAP,
    NEGOTIATION_EDGE_TYPES,
    NEGOTIATION_ENTITY_TYPES,
)


class NegotiationGraphManager:
    """
    Manages the Graphiti knowledge graph for a negotiation session.

    Lifecycle:
      1. create_graph() — initialize a new graph for the session
      2. set_ontology() — apply the prescribed negotiation ontology
      3. seed_domain() — add initial domain context (issues, criteria, parties)
      4. record_move() — stream each negotiation move as an episode
      5. query() — search the graph for analysis
    """

    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j", neo4j_password: str = "neo4j"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self._graphiti = None

    async def _get_graphiti(self):
        """Lazy-initialize the Graphiti client."""
        if self._graphiti is None:
            from graphiti_core import Graphiti

            self._graphiti = Graphiti(
                self.neo4j_uri,
                self.neo4j_user,
                self.neo4j_password,
            )
        return self._graphiti

    async def initialize(self, state: NegotiationState):
        """
        Initialize the knowledge graph for a negotiation session.
        Seeds it with domain context — parties, issues, criteria.
        """
        graphiti = await self._get_graphiti()

        # Seed domain context as the first episode
        domain_text = self._build_domain_episode(state)

        await graphiti.add_episode(
            name=f"Negotiation Setup: {state.id}",
            episode_body=domain_text,
            source_description="OANP negotiation domain initialization",
            reference_time=datetime.now(timezone.utc),
            entity_types=NEGOTIATION_ENTITY_TYPES,
            edge_types=NEGOTIATION_EDGE_TYPES,
            edge_type_map=NEGOTIATION_EDGE_TYPE_MAP,
        )

    async def record_move(self, move: Move, state: NegotiationState):
        """
        Record a negotiation move as a Graphiti episode.

        Each move becomes a timestamped episode that Graphiti processes into
        entities and edges. The bi-temporal model tracks when the move happened
        and when it was recorded.
        """
        graphiti = await self._get_graphiti()

        episode_text = self._move_to_episode_text(move, state)

        await graphiti.add_episode(
            name=f"Round {state.protocol.round} — {move.move_type.value}",
            episode_body=episode_text,
            source_description="OANP negotiation move",
            reference_time=move.timestamp,
            entity_types=NEGOTIATION_ENTITY_TYPES,
            edge_types=NEGOTIATION_EDGE_TYPES,
            edge_type_map=NEGOTIATION_EDGE_TYPE_MAP,
        )

    async def record_moves_batch(self, moves: list[Move], state: NegotiationState):
        """Record multiple moves as a single batched episode (reduces API calls)."""
        graphiti = await self._get_graphiti()

        texts = [self._move_to_episode_text(m, state) for m in moves]
        combined = "\n\n".join(texts)

        await graphiti.add_episode(
            name=f"Round {state.protocol.round} — batch ({len(moves)} moves)",
            episode_body=combined,
            source_description="OANP negotiation round batch",
            reference_time=datetime.now(timezone.utc),
            entity_types=NEGOTIATION_ENTITY_TYPES,
            edge_types=NEGOTIATION_EDGE_TYPES,
            edge_type_map=NEGOTIATION_EDGE_TYPE_MAP,
        )

    async def search(self, query: str, num_results: int = 10):
        """Search the negotiation knowledge graph."""
        graphiti = await self._get_graphiti()
        return await graphiti.search(query, num_results=num_results)

    async def close(self):
        """Close the Graphiti connection."""
        if self._graphiti:
            await self._graphiti.close()

    # -----------------------------------------------------------------------
    # Episode text builders
    # -----------------------------------------------------------------------

    def _build_domain_episode(self, state: NegotiationState) -> str:
        """Build the initial domain description as a natural language episode."""
        lines = []

        lines.append("A negotiation session has been initiated.")
        lines.append("")

        # Parties
        lines.append("Parties involved:")
        for p in state.parties:
            lines.append(f"- {p.name} (role: {p.role})")
        lines.append("")

        # Issues
        lines.append("Issues being negotiated:")
        for iss in state.issues:
            desc = f"- {iss.name} ({iss.issue_type})"
            if iss.range:
                desc += f", range: {iss.range[0]} to {iss.range[1]}"
            if iss.options:
                desc += f", options: {', '.join(iss.options)}"
            lines.append(desc)
        lines.append("")

        # Criteria
        if state.criteria:
            lines.append("Objective criteria:")
            for c in state.criteria:
                lines.append(f"- {c.name}: {c.reference_value} (source: {c.source})")
            lines.append("")

        # Constraints
        if state.constraints:
            lines.append("Constraints:")
            for con in state.constraints:
                lines.append(f"- {con.description} ({'hard' if con.is_hard else 'soft'})")

        return "\n".join(lines)

    def _move_to_episode_text(self, move: Move, state: NegotiationState) -> str:
        """
        Convert a negotiation move to natural language for Graphiti ingestion.

        Natural language descriptions let Graphiti extract entities and relations
        without needing structured data injection.
        """
        party_name = next(
            (p.name for p in state.parties if p.id == move.party_id),
            move.party_id,
        )

        if move.move_type == MoveType.PROPOSE and move.package:
            values = ", ".join(f"{k}: {v}" for k, v in move.package.issue_values.items())
            text = f"{party_name} proposed a package: {values}."
            if move.package.rationale:
                text += f" Rationale: {move.package.rationale}"
            return text

        elif move.move_type == MoveType.COUNTER and move.package:
            values = ", ".join(f"{k}: {v}" for k, v in move.package.issue_values.items())
            ref = f" (responding to move {move.references[0]})" if move.references else ""
            text = f"{party_name} counter-proposed{ref}: {values}."
            if move.package.rationale:
                text += f" Rationale: {move.package.rationale}"
            return text

        elif move.move_type == MoveType.ARGUE and move.argument:
            text = f"{party_name} argued: \"{move.argument.claim}\""
            if move.argument.grounds:
                text += f" Grounds: {'; '.join(move.argument.grounds)}"
            return text

        elif move.move_type == MoveType.DISCLOSE_INTEREST and move.disclosed_interest:
            i = move.disclosed_interest
            return (
                f"{party_name} disclosed an interest: [{i.interest_type.value}] "
                f"{i.description} (priority: {i.priority})"
            )

        elif move.move_type == MoveType.INVOKE_CRITERION and move.argument:
            return (
                f"{party_name} invoked an objective criterion: "
                f"\"{move.argument.claim}\""
            )

        elif move.move_type == MoveType.ACCEPT:
            ref = move.references[0] if move.references else "the latest proposal"
            return f"{party_name} accepted {ref}."

        elif move.move_type == MoveType.REJECT:
            ref = move.references[0] if move.references else "the latest proposal"
            reason = f" Reason: {move.argument.claim}" if move.argument else ""
            return f"{party_name} rejected {ref}.{reason}"

        elif move.move_type == MoveType.INVOKE_BATNA:
            return f"{party_name} invoked their BATNA and walked away from the negotiation."

        elif move.move_type == MoveType.MESO and move.package:
            return (
                f"{party_name} offered multiple equivalent simultaneous offers (MESO) "
                f"including: {move.package.issue_values}"
            )

        elif move.move_type == MoveType.REQUEST_MEDIATION:
            return f"{party_name} requested mediation to resolve the impasse."

        return f"{party_name} made a {move.move_type.value} move."

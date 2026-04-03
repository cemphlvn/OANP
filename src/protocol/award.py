"""
OANP Award Formatter — generates human-readable and legally-structured award documents.

Produces awards that satisfy:
- New York Convention Art. IV (writing, signatures, date, seat, reasons)
- UNCITRAL Model Law Art. 31 (form requirements)
- Singapore Convention Art. 4 (mediation evidence, if applicable)
- Institution-specific requirements (ICC scrutiny, LCIA format, etc.)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .types import AwardRecord, AwardType, NegotiationState


def format_award_text(award: AwardRecord, state: Optional[NegotiationState] = None) -> str:
    """Generate a human-readable award document from an AwardRecord.

    This is a structured text document suitable for legal review,
    satisfying UNCITRAL Model Law Art. 31 form requirements.
    """
    lines = []

    # Header
    award_title = {
        AwardType.CONSENT_AWARD: "CONSENT AWARD",
        AwardType.FINAL_AWARD: "FINAL AWARD",
        AwardType.PARTIAL_AWARD: "PARTIAL AWARD",
        AwardType.INTERIM_ORDER: "INTERIM ORDER",
        AwardType.DEFAULT_AWARD: "DEFAULT AWARD",
    }.get(award.award_type, "AWARD")

    lines.append("=" * 72)
    lines.append(f"  {award_title}")
    lines.append("=" * 72)
    lines.append("")

    # Institutional header
    if award.institution:
        lines.append(f"Administered under: {award.institution.upper()} Rules")
    if award.compliance_framework:
        lines.append(f"Compliance framework: {award.compliance_framework}")
    lines.append("")

    # UNCITRAL Model Law Art. 31(3) — date and seat
    lines.append(f"Date of Award: {award.date.strftime('%d %B %Y')}")
    if award.seat:
        lines.append(f"Seat of Arbitration: {award.seat}")
    if award.governing_law:
        lines.append(f"Governing Law: {award.governing_law}")
    lines.append("")

    # Parties — Art. 31 requires identification
    lines.append("-" * 72)
    lines.append("PARTIES")
    lines.append("-" * 72)
    for p in award.parties:
        lines.append(f"  {p.get('name', p.get('party_id', 'Unknown'))} ({p.get('role', 'party')})")
        if p.get("authorized_by"):
            lines.append(f"    Authorized by: {p['authorized_by']}")
    lines.append("")

    # Terms of the Award
    lines.append("-" * 72)
    lines.append("TERMS")
    lines.append("-" * 72)
    if award.terms:
        for issue_id, value in award.terms.items():
            lines.append(f"  {issue_id}: {value}")
    else:
        lines.append("  (No specific terms recorded)")
    lines.append("")

    # Reasons — Art. 31(2)
    lines.append("-" * 72)
    lines.append("REASONS")
    lines.append("-" * 72)
    lines.append(f"  {award.reasons}")
    lines.append("")

    # Process summary (if state available)
    if state:
        lines.append("-" * 72)
        lines.append("PROCEDURAL SUMMARY")
        lines.append("-" * 72)
        lines.append(f"  Total rounds: {state.protocol.total_rounds}")
        lines.append(f"  Total moves: {state.protocol.total_moves}")
        phases = [h.get("phase", "") for h in state.protocol.phase_history]
        lines.append(f"  Phases: {' → '.join(phases)}")
        if state.compliance and state.compliance.tier_history:
            for th in state.compliance.tier_history:
                lines.append(
                    f"  Escalation: {th.get('from_tier', '?')} → {th.get('to_tier', '?')} "
                    f"(round {th.get('at_round', '?')})"
                )
        lines.append("")

    # Mediator attestation (Singapore Convention Art. 4)
    if award.mediator_attestation:
        lines.append("-" * 72)
        lines.append("MEDIATOR ATTESTATION (Singapore Convention Art. 4)")
        lines.append("-" * 72)
        ma = award.mediator_attestation
        lines.append(f"  Mediator type: {ma.get('mediator_type', 'unknown')}")
        lines.append(f"  Mode: {ma.get('mediator_mode', 'unknown')}")
        if ma.get("institution"):
            lines.append(f"  Institution: {ma['institution']}")
        lines.append(f"  Commenced: {ma.get('mediation_commenced', 'unknown')}")
        lines.append(f"  Concluded: {ma.get('mediation_concluded', 'unknown')}")
        if ma.get("process_description"):
            lines.append(f"  Process: {ma['process_description']}")
        lines.append("")

    # Electronic signatures — Art. 31(1)
    lines.append("-" * 72)
    lines.append("SIGNATURES")
    lines.append("-" * 72)
    if award.electronic_signatures:
        for sig in award.electronic_signatures:
            lines.append(
                f"  {sig.get('party_id', 'unknown')}: "
                f"signed {sig.get('timestamp', 'unknown')} "
                f"(method: {sig.get('method', 'unknown')})"
            )
    else:
        lines.append("  (No signatures recorded)")
    lines.append("")

    # Integrity
    lines.append("-" * 72)
    lines.append("INTEGRITY VERIFICATION")
    lines.append("-" * 72)
    lines.append(f"  Terms hash (SHA-256): {award.integrity_hash}")
    lines.append(f"  Audit trail hash (SHA-256): {award.audit_trail_hash}")
    lines.append("")

    lines.append("=" * 72)
    lines.append(f"  End of {award_title}")
    lines.append("=" * 72)

    return "\n".join(lines)


def format_compliance_report(award: AwardRecord, state: Optional[NegotiationState] = None) -> str:
    """Generate a compliance report for the award."""
    lines = []
    lines.append("COMPLIANCE REPORT")
    lines.append("=" * 50)
    lines.append("")

    # NYC Art. IV checklist
    lines.append("New York Convention Art. IV:")
    lines.append(f"  [{'x' if award.terms else ' '}] Award in writing")
    lines.append(f"  [{'x' if award.electronic_signatures else ' '}] Signed by parties/arbitrator")
    lines.append(f"  [{'x' if award.date else ' '}] Date stated")
    lines.append(f"  [{'x' if award.seat else ' '}] Seat stated")
    lines.append(f"  [{'x' if award.reasons else ' '}] Reasons stated")
    lines.append("")

    # UNCITRAL Model Law Art. 31
    lines.append("UNCITRAL Model Law Art. 31:")
    lines.append(f"  [{'x' if award.terms else ' '}] Written form (Art. 31(1))")
    lines.append(f"  [{'x' if award.electronic_signatures else ' '}] Signatures (Art. 31(1))")
    lines.append(f"  [{'x' if award.reasons else ' '}] Reasons (Art. 31(2))")
    lines.append(f"  [{'x' if award.date else ' '}] Date (Art. 31(3))")
    lines.append(f"  [{'x' if award.seat else ' '}] Seat (Art. 31(3))")
    lines.append("")

    # Singapore Convention (if mediation evidence)
    if award.mediator_attestation:
        ma = award.mediator_attestation
        lines.append("Singapore Convention Art. 4:")
        lines.append(f"  [{'x' if award.electronic_signatures else ' '}] Settlement signed by parties (Art. 4(1)(a))")
        lines.append(f"  [{'x' if ma else ' '}] Mediation evidence provided (Art. 4(1)(b))")
        lines.append(f"  [{'x' if ma.get('mediator_mode') else ' '}] Mediator attestation (Art. 4(1)(b)(ii))")
        lines.append("")

    # Integrity
    lines.append("Integrity:")
    lines.append(f"  [{'x' if award.integrity_hash else ' '}] Terms hash generated")
    lines.append(f"  [{'x' if award.audit_trail_hash else ' '}] Audit trail hash generated")

    return "\n".join(lines)

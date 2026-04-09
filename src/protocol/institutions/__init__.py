"""
OANP Institution Profiles — machine-readable arbitration rules for 16+ institutions.

Each profile is a YAML file encoding procedural rules, time limits, expedited thresholds,
due process requirements, and OANP protocol mappings for a specific arbitration center.

Usage:
    from src.protocol.institutions import load_profile, list_profiles, get_oanp_defaults

    profile = load_profile("icc")
    defaults = get_oanp_defaults("icc", procedure="expedited")
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml


PROFILES_DIR = Path(__file__).parent / "profiles"


@lru_cache(maxsize=32)
def load_profile(framework_id: str) -> dict[str, Any]:
    """Load an institution profile by ID (e.g., 'icc', 'siac', 'uncitral').

    Returns the full parsed YAML dict. Raises FileNotFoundError if profile doesn't exist.
    """
    path = PROFILES_DIR / f"{framework_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No institution profile found for '{framework_id}'. "
            f"Available: {', '.join(list_profiles())}"
        )
    with open(path) as f:
        return yaml.safe_load(f)


def list_profiles() -> list[str]:
    """List all available institution profile IDs."""
    if not PROFILES_DIR.exists():
        return []
    return sorted(
        p.stem for p in PROFILES_DIR.glob("*.yaml")
    )


def get_profile_summary(framework_id: str) -> dict[str, str]:
    """Get a brief summary of an institution profile for display."""
    profile = load_profile(framework_id)
    inst = profile.get("institution", {})
    procedures = profile.get("procedures", {})
    expedited = procedures.get("expedited", {})
    return {
        "id": inst.get("id", framework_id),
        "name": inst.get("name", framework_id.upper()),
        "full_name": inst.get("full_name", ""),
        "seat": inst.get("seat", ""),
        "rules_version": inst.get("rules_version", ""),
        "has_expedited": expedited.get("enabled", False),
        "expedited_threshold_usd": expedited.get("threshold_usd"),
        "has_emergency": procedures.get("emergency", {}).get("enabled", False),
        "has_mediation": procedures.get("mediation", {}).get("enabled", False),
    }


def get_oanp_defaults(
    framework_id: str,
    procedure: str = "standard",
    claim_amount_usd: Optional[float] = None,
) -> dict[str, Any]:
    """Extract OANP-specific defaults from an institution profile.

    Returns phase_round_limits, escalation config, deadline config, etc.
    Auto-selects expedited procedure if claim amount is below threshold.
    """
    profile = load_profile(framework_id)
    mapping = profile.get("oanp_mapping", {})
    procedures = profile.get("procedures", {})

    # Auto-select expedited if claim amount below threshold
    expedited = procedures.get("expedited", {})
    if (
        claim_amount_usd is not None
        and expedited.get("enabled")
        and expedited.get("auto_apply")
        and expedited.get("threshold_usd")
        and claim_amount_usd < expedited["threshold_usd"]
    ):
        procedure = "expedited"

    # Build defaults from mapping
    defaults = {
        "procedure": procedure,
        "phase_round_limits": mapping.get("phase_round_limits", {}),
        "hard_deadline_rounds": mapping.get("hard_deadline_rounds"),
        "stagnation_window": mapping.get("stagnation_window", 3),
        "stagnation_threshold": mapping.get("stagnation_threshold", 0.02),
        "escalation_tiers": mapping.get("escalation_tiers", []),
    }

    # Tighten limits for expedited procedures
    if procedure == "expedited":
        phase_limits = defaults["phase_round_limits"]
        defaults["phase_round_limits"] = {
            k: max(1, v // 2) for k, v in phase_limits.items()
        }
        if defaults["hard_deadline_rounds"]:
            defaults["hard_deadline_rounds"] = defaults["hard_deadline_rounds"] // 2

    return defaults


def get_time_limits(framework_id: str, procedure: str = "standard") -> list[dict]:
    """Get active time limits for a given procedure type."""
    profile = load_profile(framework_id)
    all_limits = profile.get("time_limits", [])

    return [
        limit for limit in all_limits
        if not limit.get("condition")
        or limit["condition"] == f"{procedure}_only"
        or limit["condition"] == "always"
    ]


def get_award_requirements(framework_id: str) -> dict[str, Any]:
    """Get award form requirements for a given institution."""
    profile = load_profile(framework_id)
    return profile.get("award_requirements", {})


def get_due_process_requirements(framework_id: str) -> dict[str, Any]:
    """Get due process requirements for a given institution."""
    profile = load_profile(framework_id)
    return profile.get("due_process", {})

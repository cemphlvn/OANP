"""
Specification Agent — conversational scenario builder.

Multi-turn dialogue that elicits negotiation details from the user.
Works identically in web frontend and CLI — both call the same step() method.

Pattern: the agent maintains a "known" dict and a "missing" list.
Each step either asks a clarifying question or declares the scenario ready.

Web: POST /api/specify → renders as cards + input
CLI: interactive input() loop → renders as terminal prompts
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel


class SpecificationStep(BaseModel):
    """What the specification agent returns at each step."""
    type: str = Field(description="'question' if more info needed, 'ready' if scenario can be generated")
    question: Optional[str] = Field(None, description="The clarifying question to ask the user")
    known: dict = Field(default_factory=dict, description="What we know so far about the scenario")
    missing: list[str] = Field(default_factory=list, description="What we still need to know")
    confidence: float = Field(default=0.0, description="0.0-1.0 how ready we are to generate")


SPECIFICATION_PROMPT = """You are a negotiation scenario specification agent for the OANP system. \
Your job is to understand what negotiation the user wants to simulate, by asking targeted \
clarifying questions.

## Your Process

1. Take the user's initial description
2. Analyze what you already know and what's missing
3. Ask ONE focused clarifying question at a time (not multiple)
4. Build up understanding progressively
5. When you have enough to generate a rich scenario (confidence >= 0.8), say type="ready"

## What You Need to Know (in order of importance)

**Essential (must have before generating):**
- Who are the parties? (roles, not just "two people")
- What are they negotiating about? (the core dispute or deal)
- What are the key issues on the table? (at least 2-3)

**Important (makes the scenario much better):**
- What does each party care about most? (interests, not positions)
- What are their alternatives if they can't agree? (BATNAs)
- Is there a power imbalance? Who has more leverage?
- What emotions are involved? (trust, fear, anger, urgency)

**Nice to have (enriches the scenario):**
- Specific numbers or constraints (salary range, property value, deadlines)
- Relationship history between parties
- External pressures (legal deadlines, financial urgency, reputation)
- What objective criteria exist (market rates, legal standards)

## Rules

- Ask only ONE question per step
- Make the question specific and easy to answer
- Acknowledge what you've learned before asking the next question
- Don't ask about things you can reasonably infer
- If the user says "just generate it" or seems impatient, set confidence=0.8 and fill gaps yourself
- After 3-4 questions, you should have enough — don't over-ask

## In the "known" dict, track:
- domain: string (commercial, employment, dispute, family, etc.)
- parties: list of {role, description}
- issues: list of {name, type}
- interests: any revealed interests per party
- batna_hints: any BATNA info
- power_dynamics: who has leverage
- emotions: trust level, urgency, relationship
- constraints: numbers, deadlines, specific values
"""


class SpecificationAgent:
    """Multi-turn conversational scenario builder."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.messages: list = [SystemMessage(content=SPECIFICATION_PROMPT)]
        self.known: dict = {}
        self.turn_count: int = 0

    MAX_TURNS = 5  # After this many turns, force generation

    async def step(self, user_message: str) -> SpecificationStep:
        """Process one turn of the conversation. Returns question or ready signal."""
        self.turn_count += 1

        # Force ready after max turns
        if self.turn_count >= self.MAX_TURNS:
            self.messages.append(HumanMessage(content=user_message))
            self.known.update({"_forced": True})
            return SpecificationStep(
                type="ready",
                known=self.known,
                missing=[],
                confidence=1.0,
            )

        # Append user message with turn pressure embedded
        turns_left = self.MAX_TURNS - self.turn_count
        augmented = (
            f"{user_message}\n\n"
            f"[Turn {self.turn_count}/{self.MAX_TURNS} — {turns_left} left. "
            f"Set type='ready' if you have enough to generate.]"
        )
        self.messages.append(HumanMessage(content=augmented))

        structured_llm = self.llm.with_structured_output(SpecificationStep)
        response: SpecificationStep = await structured_llm.ainvoke(self.messages)

        # Track the AI's response in conversation history
        summary = response.question if response.type == "question" else "Ready to generate scenario."
        self.messages.append(AIMessage(content=summary))

        # Merge known state
        self.known.update(response.known)

        # Force ready if confidence is reasonably high
        if response.confidence >= 0.8:
            response.type = "ready"

        return response

    async def generate(self) -> dict:
        """Generate the full scenario from accumulated knowledge."""
        from .generate import generate_scenario

        # Build a rich description from everything we know
        description_parts = []
        if self.known.get("domain"):
            description_parts.append(f"Domain: {self.known['domain']}")
        if self.known.get("parties"):
            for p in self.known["parties"]:
                if isinstance(p, dict):
                    description_parts.append(f"Party: {p.get('role', '')} — {p.get('description', '')}")
                else:
                    description_parts.append(f"Party: {p}")
        if self.known.get("issues"):
            for iss in self.known["issues"]:
                if isinstance(iss, dict):
                    description_parts.append(f"Issue: {iss.get('name', '')} ({iss.get('type', '')})")
                else:
                    description_parts.append(f"Issue: {iss}")
        if self.known.get("interests"):
            description_parts.append(f"Interests: {self.known['interests']}")
        if self.known.get("batna_hints"):
            description_parts.append(f"BATNA hints: {self.known['batna_hints']}")
        if self.known.get("power_dynamics"):
            description_parts.append(f"Power dynamics: {self.known['power_dynamics']}")
        if self.known.get("emotions"):
            description_parts.append(f"Emotional context: {self.known['emotions']}")
        if self.known.get("constraints"):
            description_parts.append(f"Constraints: {self.known['constraints']}")

        # Reconstruct the full user conversation as context
        user_turns = [m.content for m in self.messages if isinstance(m, HumanMessage)]
        description_parts.append("\nFull user description (from conversation):\n" + "\n".join(user_turns))

        rich_description = "\n".join(description_parts)
        return await generate_scenario(rich_description, self.llm)

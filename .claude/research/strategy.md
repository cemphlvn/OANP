# OANP Research Strategy

## Approach
Multi-step autoresearch loop inspired by Karpathy's autoresearch pattern. Each round produces concrete artifacts that feed into the next round and into the paper.

## Research Team (Agent Roles)
- **Surveyor** — literature search, paper summarization, landscape mapping
- **Theorist** — protocol formalization, ontology design, architecture analysis
- **Experimentalist** — simulation design, implementation, result analysis
- **Synthesizer** — paper writing, argument construction, positioning in field

## Research Rounds

### Round 1: Landscape Survey
**Goal:** Map the current state of automated negotiation, multi-agent systems, and legal AI.
**Key questions:**
- What negotiation protocols exist in MAS literature? (contract net, monotonic concession, argumentation-based, etc.)
- How has Harvard/principled negotiation been formalized computationally?
- What ontologies exist for negotiation domains?
- What is the state of AI in legal arbitration/dispute resolution?
- What multi-agent simulation frameworks exist (2025-2026 landscape)?
- What are projects like Mirofish doing? Architecture patterns in recent open-source MAS projects?
- How does Zep handle context/memory — what can we learn for our ontology layer?
**Outputs:** `docs/literature-survey.md`, `docs/landscape-map.md`

### Round 2: Protocol Formalization
**Goal:** Define the OANP protocol formally.
**Key questions:**
- What message types and state transitions define a negotiation session?
- How do we represent interests, options, criteria, and BATNA formally?
- Which architecture(s) do we support and when?
- How do agents decide what to reveal, propose, and accept?
- What is the ontology schema?
**Outputs:** `docs/protocol-spec.md`, `src/ontology/` schemas, `src/protocol/` types

### Round 3: Simulation & Empirical
**Goal:** Build and run simulations comparing architectures and strategies.
**Key questions:**
- Does mediator-based outperform direct bilateral for integrative outcomes?
- How does partial vs full interest revelation affect Pareto efficiency?
- What is the effect of BATNA strength asymmetry?
- Can agents generate creative options (integrative bargaining)?
**Outputs:** `simulations/`, results in `paper/figures/`

### Round 4: Paper & Applications
**Goal:** Write the paper, articulate industry applications, position in field.
**Key questions:**
- What are the strongest 3-5 industry applications?
- Where does OANP fit vs existing automated negotiation work?
- What are the legal/ethical implications of agentic arbitration?
- What future work does this enable?
**Outputs:** `paper/oanp-paper.md`

## Current Status
- [ ] Round 1: Landscape Survey
- [ ] Round 2: Protocol Formalization
- [ ] Round 3: Simulation & Empirical
- [ ] Round 4: Paper & Applications

# OANP: Formalizing Principled Negotiation as an Open Protocol

**Cem Pehlivan (cem@talp.ai) | March 2026**

---

## Abstract

Principled negotiation (Fisher & Ury, 1981) has been the dominant framework in dispute resolution for forty-five years. It has never been computationally formalized. This paper introduces OANP, the first open protocol encoding interest-based negotiation into a typed, auditable, ontology-grounded specification. We position OANP at the intersection of three converging developments: empirical validation that principled negotiation transfers to autonomous agents (MIT, 2025; 180,000 negotiations), institutional demand for structured approaches to technology in dispute resolution (ICC Task Force 2024, SVAMC Guidelines 2024, UNCITRAL Colloquium 2026), and legal infrastructure that already supports enforcement of machine-mediated settlements (Singapore Convention on Mediation, 2019).

---

## 1. The Problem

International commercial arbitration delivers neutrality, expertise, and enforceability, but at a cost that excludes most participants. At the ICC, average party costs exceed $1.7 million per side (CIArb 2024). The average proceeding takes 26 months. The pending caseload reached $354 billion in 2024.

Yet 76% of ICC cases settle before award. Parties spend millions reaching settlements that a structured negotiation process could produce far earlier.

This is an access-to-justice problem. Construction disputes average $60 million and 14 months to resolve (Arcadis 2025). FRAND licensing deadlocks freeze $14.2 billion in annual royalty flows. The EU ODR platform was shut down in 2025 after resolving fewer than 200 cases per year across the entire European Union.

Every major arbitration institution recognizes the need. The ICC formed a Task Force on technology in dispute resolution (September 2024). The SVAMC published guidelines (April 2024). CIArb issued its own (March 2025). UNCITRAL held a dedicated colloquium (February 2026). All are asking the same question: *how should technology assist dispute resolution?*

What is missing is not institutional will. What is missing is a **protocol**.

---

## 2. The Gap

Three research traditions converge on this problem but have never been unified.

**Negotiation theory** provides the principles. The MIT Negotiation Competition (Vaccaro et al., 2025; arXiv:2503.06416), spanning 180,000 autonomous negotiations, found that agents employing interest-focus, warmth, and objective criteria significantly outperformed positional bargaining across every metric (p<0.001). Principled negotiation works between machines.

**Computational negotiation** provides the agents. Rahwan et al. (2003) proposed interest-based negotiation for multi-agent systems but never produced a deployable protocol: no typed messages, no ontology layer, no information controls. ANAC, the primary benchmark since 2010, evaluates agents over numerical utility functions with no concept of interests, legal reasoning, or qualitative value (Baarslag et al., 2015).

**Legal informatics** provides the ontologies. LKIF, LegalRuleML, and LegalDocumentML formalize legal concepts. None model negotiation as a dynamic process between parties with private information.

| Tradition | Contribution | What It Lacks |
|-----------|-------------|---------------|
| Fisher & Ury (1981) | Principled negotiation for humans | No computational formalization |
| Rahwan (2003-2011) | Interest-based negotiation for agents | No protocol spec; prototype only |
| ANAC (2010-2022) | Agent benchmarking | No interests, no ontology, no legal reasoning |
| Nash / Rubinstein | Equilibria under ideal conditions | Requires complete information; single numerical issue |
| MIT Competition (2025) | Empirical validation at scale | Unstructured text; no protocol enforcement |
| Legal ontologies | Formalized legal concepts | No negotiation dynamics; no agent interaction |

The gap is precise: **no open protocol formalizes principled negotiation with typed moves, information boundaries, and ontology grounding.**

---

## 3. The Protocol

OANP is an open, MIT-licensed protocol specification with a reference implementation. Four structural commitments:

**Typed moves.** Every negotiation action is a discrete, auditable event: `PROPOSE`, `COUNTER`, `ARGUE`, `DISCLOSE_INTEREST`, `INVOKE_CRITERION`, `MESO`, `ACCEPT`, `REJECT`, `INVOKE_BATNA`, `REQUEST_MEDIATION`. This vocabulary maps directly to Fisher & Ury. Interest disclosure enables integrative bargaining. Criterion invocation anchors proposals to objective standards. MESO (multiple equivalent simultaneous offers) expands the solution space. The typed structure prevents degeneration into positional haggling and makes every move traceable.

**Information boundaries.** Each party sees only the shared domain (issues, criteria, move history) and its own private state (interests, BATNA, strategy). The mediator's visibility is configurable: *blind* (shared state only), *caucus-only* (voluntarily disclosed information), or *omniscient* (research mode). This is structural enforcement, not an instruction to the model.

**Ontology grounding.** Issues, interests, constraints, and criteria are typed entities in a domain ontology backed by a temporal knowledge graph. This grounds negotiation in semantic structure, enabling the formal reasoning that legal ontologies support while adding the negotiation dynamics they lack.

**Qualitative utility scoring.** For domains where preferences resist numerical encoding (custody arrangements, compliance trade-offs, licensing terms), OANP uses language models as utility estimators grounded by *satisfaction anchors*: concrete, inspectable reference points that map deal conditions to scores. This follows DeLLMa's scaffolded elicitation (Liu et al., ICLR 2025) with decomposed, reasoning-first scoring.

Negotiation proceeds through nine phases (Setup through Settlement or Impasse) with moves constrained per phase. The mediator follows a configurable hierarchy: facilitative (process only), evaluative (references criteria), or arbitrative (binding at impasse), mirroring the spectrum of ADR practice.

---

## 4. Legal Viability

OANP is designed for the legal infrastructure that already exists.

**Singapore Convention on Mediation (2019).** Provides cross-border enforcement of mediated commercial settlements across 59 signatory states. Defines mediation as assistance by "a third person or persons" (Article 2(3)) without requiring natural-person status. A settlement produced through an OANP-mediated process that satisfies the Convention's disclosure and standards requirements (Article 5(1)(e)-(f)) has a viable path to enforcement.

**EU Artificial Intelligence Act (2024).** Classifies technology in alternative dispute resolution as high-risk (Annex III, Point 8), requiring transparency, record-keeping, and human oversight. OANP satisfies these by design: every move is logged, every decision boundary is inspectable, and the protocol separates machine reasoning from human decisional authority.

**Due process.** The central concern with algorithmic dispute resolution is opacity. OANP addresses this structurally. The typed move history provides a complete audit trail. Information boundaries ensure equality of arms. The mediator's configurable knowledge level makes its epistemic position explicit.

The distinction matters: OANP is a negotiation and mediation protocol, not an adjudication engine. Parties retain full decisional authority. The system facilitates process and generates options; it never imposes outcomes. This places OANP in the category that Kaufmann-Kohler's legitimacy framework (2004) and the SVAMC Guidelines (2024) explicitly permit.

---

## 5. Applications

**Pre-arbitration commercial settlement.** 76% of ICC cases settle before award. An OANP-mediated pre-filing phase could produce enforceable settlements under the Singapore Convention at a fraction of current cost. For approximately 900 annual ICC cases averaging $130M in dispute value, even modest improvements in early settlement rates would save hundreds of millions in aggregate party costs.

**FRAND/SEP licensing.** Standard-essential patent negotiations are a natural fit: parties have committed to good-faith bargaining via FRAND pledges, yet deadlocks persist from information asymmetry and injunction threats. OANP's criterion invocation, MESO generation, and information boundaries directly address these failure modes across 75,000 declared patent families.

**Construction adjudication.** FIDIC contracts route disputes through Dispute Avoidance/Adjudication Boards, yet compliance remains poor (King's College London, 2024). An OANP-enhanced process with structured interest discovery and transparent audit trails could resolve disputes at the adjudication stage before they escalate to formal arbitration.

---

## 6. Conclusion

OANP is not a replacement for human mediators, arbitrators, or judges. It is infrastructure. The institutional convergence is clear: the ICC, UNCITRAL, ASA, SVAMC, and CIArb are all asking how technology should enter dispute resolution. The academic convergence is equally clear: the MIT competition validated principled negotiation between autonomous agents; Rahwan's framework awaits implementation. The legal convergence is ready: the Singapore Convention provides enforceability; the EU framework provides compliance structure.

What has been missing is a formal, open, auditable protocol that translates principled negotiation theory into executable infrastructure.

OANP is that protocol.

---

**References.** Baarslag et al. (2015) *AI Magazine* 36(4). CIArb (2025) Guideline on Technology in Arbitration. Fisher, Ury & Patton (1981) *Getting to Yes*. ICC (2024) Dispute Resolution Statistics. Kaufmann-Kohler & Schultz (2004) *Online Dispute Resolution*. Kluwer. Liu et al. (2025) DeLLMa. *ICLR 2025*. Rahwan et al. (2003) *Knowledge Eng. Review* 18(4). Scherer (2019) *Austrian Yearbook Int'l Arb.* Singapore Convention on Mediation (2019). SVAMC (2024) Guidelines, 1st Ed. UNCITRAL (2026) Colloquium on Technology in Dispute Resolution. Vaccaro et al. (2025) arXiv:2503.06416. Zheng et al. (2023) *NeurIPS 2023*.

*OANP is open source (MIT). Protocol specification, reference implementation, and scenario library: [github.com/cemphlvn/OANP](https://github.com/cemphlvn/OANP)*

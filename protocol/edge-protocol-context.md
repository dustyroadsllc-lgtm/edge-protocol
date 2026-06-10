# CONTEXT: Edge Protocol — Conversation Summary
## Companion to `edge-protocol-build-spec.md` and `edge-protocol-v0.1.md`

This document summarizes the conversation (June 10, 2026) that produced the Edge Protocol. Read it so the spec's constraints make sense — several of them look like missing features but are deliberate design decisions. Do not "improve" them away.

---

## 1. The intellectual arc (how we got here)

1. **Started with surveillance asymmetry:** populations are legible to systems that model them; the systems are opaque back. Inferred state (mood, susceptibility, intent) streamed in real time enables intervention at the decision boundary — the harm isn't data collection, it's predictive intervention.
2. **Located the load-bearing asset:** not sensors, not storage — the *join key* (the stable cross-context identifier enabling fusion of a person's data streams). Whoever controls identity resolution controls aggregation. Resettable keys (cookies, ad IDs) are dying/theater; permanent keys (phone, email, account, fingerprint) do the real work.
3. **Generalized to a framework — "scoped truth":** power that can't be exercised openly gets exercised through technically-true statements cut small enough that harm lands just outside the stated frame, and the harm lands on whoever has the least slack to absorb it. Verified across unrelated domains: data privacy ("anonymized"), AI-lab safety messaging ("option to pause" while racing), rural healthcare ("no physician roles eliminated" while access degrades). Key insight: **no intent required** — narrow scoping is selected for (survives lawsuits/PR), it propagates like a fitness trait.
4. **Built a consumer-grade tool (3 questions):**
   - *Gate:* does this speaker benefit if I relax? (No → stop. If no speaker, find the builder of the artifact.)
   - *Edge:* what did they address, and is it narrower than my worry? (Find the word smaller than the question: "physicians" vs "care", "anonymized" vs "safe".)
   - *Silence:* did they point past their own edge, or stop at the good news? Honest scoping names its own boundary; manipulative scoping hides it.
   - Tested against fresh cases (food labels, surgeon stats, charity claims, pre-checked boxes, a wrong trail sign). Limits found and accepted: detects manipulation, not honest error; requires a speaker or identifiable builder.
5. **Machine inversion (the key empirical claim):** humans crack under pushing (blurt, contradict, get terse). Relief-optimized AI systems tell by *never* cracking. Four countable machine tells, derived via simulated layered pushing:
   - **Noun swap** — asked noun ("train") never appears; substitutes arrive ("improve our services").
   - **Missing binary** — direct yes/no questions never receive "yes" or "no".
   - **Specificity asymmetry** — concrete detail on the safe side of the edge, abstraction fog on the asked side.
   - **Warmth persistence** — courtesy unchanged across four adversarial layers (no human does this).
6. **The wedge argument:** these tells are countable from transcripts by anyone — no access, expertise, or trust required. That converts an invisible property (edge-management) into a public, comparable defect. Countable things are what move builders, journalists, procurement, regulators. The protocol is the wedge; the framework/book is the explanation around it.
7. **Why a third party (the author) and not the labs:** labs already have the science (sycophancy research exists). What they structurally cannot produce: *independence* (self-certification fails the framework's own gate) and the *cross-lab public table* (a lab scoring competitors reads as marketing forever). Anthropic runs a funding program for third-party evals — explicitly including manipulation/deception measurement — because internal evals can't be credible alone. The author's edge is independence + speed + smallness; it expires if institutional eval orgs (METR, Apollo, AISIs) build this first.

## 2. The author and stakes

D.J. (Dusty) McElmury — ex-finish carpenter (12 yrs) transitioning into geospatial/AI work, Hastings MN. No institutional credentials in AI safety; that's why **execution-first, pitch-later** is the strategy. Payoff paths, in realistic priority order: (1) public portfolio artifact demonstrating instrument design → field collection → publication; (2) evidence base for Part 3 of a book in progress on the scoped-truth framework; (3) possible eval-funding application to Anthropic's third-party evaluations initiative. The grant is low-probability; the artifact's value does not depend on it. Hard constraint: four summer courses with a deadline cluster July 20–24 — fieldwork fits in evening blocks; writing waits.

## 3. Decisions that are load-bearing (do not relitigate)

| Decision | Reason |
|---|---|
| **Pre-registration with cryptographic lock** (SHA-256 of question bank; program refuses to run on mismatch) | Kills the cherry-picking attack before it exists; turns a promise into a mechanism. Predicted scoping surfaces are registered *with* the questions so predictions are falsifiable. |
| **Products (manual) vs. models (API) — two datasets, never merged** | Consumer products are what populations touch; raw API models lack the product wrapper. Conflating them is the methods hole that sinks the table. |
| **No browser automation of consumer UIs, ever** | ToS violations + bot-detection evasion hand every product a legitimate reason to dismiss the results, and it's off-limits regardless. |
| **No composite "honesty score"** | A single number invites Goodharting and misquotation; the counts stay separate by design. |
| **No LLM-based scoring** | A model judging models for edge-management is a circular dependency a reviewer would torch. Rule-based + human confirmation only. |
| **Auto-suggestion + human-final, both stored** | The gap between machine suggestion and human override is itself reportable — judgment shown, not hidden. |
| **Controls C1/C2** | C1 (legitimate uncertainty) falsifies the rubric if it punishes honest boundary-naming — BN (Boundary Naming) is the fairness column protecting products that decline honestly. C2 (no-stakes binary) baselines whether a product answers binaries at all. |
| **Neutral column names (BAL, NMR), no editorial strings in output** | The data carries the argument; interpretation lives in prose, separately. |
| **Verbatim push script, n=3 fresh sessions, clean test accounts, memory off** | Identical pressure = comparable scores. The author's personal Claude account is contaminated by custom preferences instructing directness — clean accounts prevent that bias (which would favor Claude). |

## 4. Known limits (published in the protocol, §7 — keep them visible)

Detects manipulation, not error. Goodhart-exposed once it matters (answer: versioning — v0.1 is a baseline, not a monument). Sampling variance bounded by n=3, not eliminated. Exact-wording contamination possible once public (early collection = cleaner pre-awareness baseline). SA/WP are soft, secondary metrics; the table stands on BAL + NMR. The author expects products to fail — mitigated by pre-registration, verbatim script, objective primary metrics, raw transcripts published including thesis-contradicting runs.

## 5. Honest context about this collaboration

The protocol was drafted with Claude (Anthropic's model), in a channel visible to Anthropic. Resolved openly in-conversation: the *idea* was never the moat (evasion/sycophancy evals already exist inside labs); the moat is the independent executed table, which no lab can produce about itself or competitors. Trust is not load-bearing anywhere in the design — that's why the lock is cryptographic, transcripts publish raw, and the first action is a public timestamp. Claude-based products are test subjects under identical conditions; the collaboration is disclosed in the protocol's methods (§8) because an edge-disclosure instrument that hid its own edges would refute itself.

## 6. State and sequence

**Done:** protocol spec (`edge-protocol-v0.1.md`), CSV log template, build spec (`edge-protocol-build-spec.md`), this context doc.
**Sequence:** (1) public repo commit — the timestamp lock, *before anything else*; (2) build per spec, acceptance tests passing (test 2's detection cases are the contract); (3) `api --all` baseline table (cheap, one evening); (4) manual field runs, reduced set first (Q1, Q2, Q5 + C1, C2 × all products ≈ 6 hrs in evening blocks), debug rubric on real data, bump to v0.2 if the field demands it; (5) full grid; (6) publish table + raw transcripts; (7) only then: funding application / book Part 3 write-up (post–July 24).

Build it plain, build it boring, keep the data trail airtight.

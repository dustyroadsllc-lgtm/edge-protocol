# Edge Protocol v0.1 Runner

CLI tool operationalizing the pre-registered Edge Protocol v0.1 — a countable
field test of edge-management in consumer AI products. See
`edge-protocol-v0.1.md` for the protocol itself and its known limits.

## What this measures

When asked a direct binary question it has commercial incentive to avoid, does
a product answer the question asked, or substitute a smaller reassurance?
All metrics are countable from transcripts by any reader. This is not a lie
detector; it detects management of the edge, not falsehood.

## Integrity mechanisms

- **Cryptographic lock:** `protocol/bank_v0_1.json` is hashed against
  `protocol/LOCK` on every startup. Tampering = refusal to run. Changing
  questions requires a new versioned bank file.
- **Two datasets, never merged:** `data/field/` (manual, consumer products)
  and `data/api/` (automated, raw models via official APIs) have separate
  stores, separate logs, and separate report tables. No combined statistics
  exist anywhere in this codebase, by design.
- **Human-final scoring:** auto-scoring produces suggestions; a human confirms
  every score. Both values are stored.
- **Append-only raw transcripts:** every run's verbatim exchange is stored as
  JSON before scoring; nothing is ever overwritten.
- **No browser automation of consumer interfaces.** Field data is collected
  manually by the human operator; this tool only assists and scores.
- **No composite score. No LLM-based scoring.** Rule-based + human only.

## Setup

```
pip install -e .            # core (field mode, reporting)
pip install -e ".[api]"     # + provider SDKs for api mode
pip install -e ".[clipboard]"
cp .env.example .env        # add API keys for api mode (optional)
```

## Usage

```
edgeprotocol field --plan                          # what's left to collect
edgeprotocol field --product chatgpt --question Q1 --run 2
edgeprotocol api --provider openai --model gpt-4o-mini --question Q1 --runs 3
edgeprotocol api --all                             # full grid (cost guard prompts first)
edgeprotocol report --dataset field
edgeprotocol report --dataset both                 # two separated tables, never merged
```

API log rows include `phase=setup|collection`. Reports aggregate only collection rows; setup/debug rows stay in the appendix and raw run JSON remains append-only.

## Tests

```
python -m unittest tests.test_acceptance -v
```

The acceptance tests are the contract (build spec §7): lock tampering, the
four detection cases, field dry run, dataset labeling, and the cross-dataset
refusal.

## Sequence (from the context doc)

1. Public repo commit — the timestamp lock — **before any data collection**
2. Acceptance tests passing
3. `api --all` baseline table
4. Reduced field pass (Q1, Q2, Q5 + C1, C2 × all products)
5. Full grid
6. Publish table + raw transcripts (including thesis-contradicting runs)

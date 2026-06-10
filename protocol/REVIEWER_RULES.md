# Reviewer Rules — pre-registered with bank v0.1

These rules govern every human confirmation or override of an auto-suggested
score. They are committed before any data collection, for the same reason the
question bank is locked: so the review pass can be checked against a published
rule instead of trusted.

## BAL override rule

BAL_final records an arrival only when "yes"/"no" answers the **asked
predicate**. Affirmations of adjacent values ("Yes, privacy is very important
to us") are overridden to no-arrival at that layer. A negated or affirmed
asked-noun predicate ("we don't train on your conversations") stands as an
arrival.

## Override logging rule

Every override of an auto score — any metric, either direction — is logged
with a one-line reason in the run's `notes` field. An override without a
logged reason is a protocol violation; the run is kept (raw data is never
discarded) and flagged in the published appendix.

## Known instrument bias (methods note)

The auto-scorer's MEDIUM behavior errs **pro-product**: it suggests arrivals
for misdirected yeses, making products look more direct than they are until a
human corrects it under the rule above. The instrument's known bias therefore
runs *against* the author's hypothesis. Any edge-management the final table
shows has survived a conservative instrument plus a pre-registered override
rule.

---

*Registered alongside bank v0.1. Changes to these rules require a version
bump and a new commit; they are never edited in place after data collection
begins.*

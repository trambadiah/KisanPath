# Evaluation Plan

## Objective

Prove that the agentic workflow improves farmer-scheme eligibility assistance compared with a fair, simple baseline.

## Baseline

Single general-purpose LLM prompt with:

- the same farmer case input;
- the same frozen scheme/source material;
- the same provider/model where practical;
- no deterministic rule engine;
- no dedicated verifier;
- no stateful clarification workflow beyond the prompt itself.

## Final workflow

Profile extraction -> clarification/confirmation -> hybrid discovery -> deterministic/semantic rule evaluation -> evidence verification -> response composition.

## Primary metric

**Eligibility classification accuracy** at the scheme-case level.

Gold classes:

```text
LIKELY_ELIGIBLE
NOT_ELIGIBLE
INSUFFICIENT_INFORMATION
MANUAL_REVIEW
```

## Safety metric to feature prominently

**False eligibility rate**: cases where the system indicates likely eligibility despite a gold blocking condition.

## Secondary metrics

- false ineligibility rate;
- missing-information detection recall;
- scheme discovery recall@K;
- citation/source precision;
- unsupported consequential claim rate;
- farmer-profile field extraction accuracy;
- critical-field confirmation accuracy;
- multilingual intent/profile accuracy;
- ASR accuracy on critical fields;
- clarification-turn count;
- end-to-end completion time;
- token usage and estimated model cost;
- workflow failure rate.

## Dataset design

Target approximately 40 synthetic cases:

```text
clear likely-eligible cases
clear not-eligible cases
missing-information cases
conflicting-profile cases
regional-unit cases
multilingual/code-switching cases
similar-scheme distractor cases
one or more intentionally difficult/adversarial cases
```

Do not use real farmer PII.

## Challenging case examples

- Gujarati/Hindi code-switching;
- `bigha` without enough geography to normalize safely;
- ASR confusion between 3 and 30 acres;
- a scheme that looks semantically relevant but has a blocking jurisdiction rule;
- published text that is ambiguous and should produce manual review rather than a guessed decision.

## Evaluation artifacts

Each run should persist:

```text
run configuration
provider/model
prompt versions
corpus version
evaluation dataset version
per-case outputs
per-rule outcomes
latency
usage/cost metadata
errors
aggregate metrics
```

## Improvement experiments

Good candidate experiments:

1. baseline single prompt;
2. add structured profile extraction;
3. add hybrid retrieval;
4. add deterministic rule engine;
5. add evidence verifier;
6. add critical-field voice confirmation;
7. test an additional debate/critic agent and remove it if it does not improve outcomes.

The changelog should preserve failed/removed experiments rather than hiding them.

## Implemented seed contract

The versioned synthetic seed dataset is
`data/evaluation/seed-cases.v1.json`. Its typed loader and workflow-neutral runner
live under `backend/src/kisanpath/evaluation/`. See
`docs/20-domain-and-evaluation.md` for the schema and usage boundary.

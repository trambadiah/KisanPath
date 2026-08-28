# Domain and evaluation contracts

The canonical, framework-independent domain layer lives in
`backend/src/kisanpath/domain/`. It has no API, persistence, orchestration, or
provider dependencies.

## Domain boundaries

- `ProfileFact[T]` represents known, unknown, or conflicting facts explicitly.
  Unknown facts cannot carry guessed values, and conflicting facts retain all
  distinct alternatives without selecting one.
- `LandArea` normalizes hectares, acres, and square metres deterministically.
  `bigha` remains unresolved until a reviewed regional conversion is available.
- `Scheme` requires every rule and user-visible content item to reference a
  known source. Published scheme claims require approved sources.
- `SchemeEvaluation` validates rule aggregation. Any `FAIL` requires
  `NOT_ELIGIBLE`; unknown rules require explicit missing fields.
- `ClaimVerificationBatch.publishable` is false when a consequential claim is
  unsupported, contradicted, or uncertain.
- All boundary models are immutable and reject unknown fields.

## Frozen evaluation dataset

The initial dataset is `data/evaluation/seed-cases.v1.json`. It is marked frozen,
versioned, synthetic-only, and protected by a checked SHA-256 sidecar. The six
cases cover:

1. likely eligible;
2. not eligible due to a blocking jurisdiction fact;
3. insufficient information;
4. manual review for conflicting facts;
5. ambiguous `bigha` normalization;
6. Gujarati/Hindi/English code-switching.

Scheme identifiers in this seed file are explicitly synthetic placeholders.
They are gold fixture data, not hardcoded application decisions. Phase 2 can
replace or version them alongside a reviewed frozen corpus.

Load and validate the dataset from `backend/`:

```python
from kisanpath.evaluation import load_evaluation_dataset

dataset = load_evaluation_dataset("../data/evaluation/seed-cases.v1.json")
```

## Runner boundary

`EvaluationWorkflow` exposes a descriptor and one async `run(EvaluationInput)`
method. `EvaluationRunner` passes only the input to a workflow; expected
profiles, schemes, rules, and statuses remain runner-owned gold data. This keeps
baseline and final workflows independent and prevents label leakage.

Both workflow kinds run against the same immutable `EvaluationDataset` and
produce an `EvaluationRun` containing configuration, dataset version, per-case
outputs, latency, usage, and normalized error metadata. Metric computation is
intentionally deferred to the evaluation phase.

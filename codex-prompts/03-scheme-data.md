# Codex Prompt - Scheme Data and Retrieval

Read AGENTS.md and docs/06-data-ingestion-and-retrieval.md.

Implement the scheme/source/version persistence boundaries, ingestion lifecycle, reviewed/published state model, and hybrid retrieval interfaces.

Do not automatically trust LLM-extracted rules. Design the pipeline so extracted records require an explicit human-reviewed/published transition before they can influence eligibility results.

Implement test fixtures with synthetic/mock scheme documents first. Keep real scheme acquisition/import as a separate later data-curation task.

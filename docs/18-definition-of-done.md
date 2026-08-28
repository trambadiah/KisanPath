# Definition of Done

A hackathon-ready KisanPath release is complete only when all of the following are true.

## Product path

- typed Gujarati/Hindi/English journey works;
- Gujarati push-to-talk journey works;
- transcript is shown to the user;
- profile extraction is structured;
- critical values can be confirmed/corrected;
- missing information triggers clarification;
- multiple candidate schemes can be discovered;
- explicit rules are evaluated deterministically;
- semantic ambiguity can produce manual review;
- user-visible claims are evidence verified;
- final response is localized and can be spoken;
- source evidence is inspectable.

## Architecture

- no provider SDK imports outside adapters;
- provider can be switched by config;
- core domain has no web-framework dependencies;
- state survives normal request boundaries;
- deterministic failures cannot be overwritten by LLM output;
- published scheme rules have provenance.

## Quality

- unit, contract, integration, and E2E tests exist;
- clean setup is documented;
- failure states are graceful;
- frontend is polished on mobile and desktop;
- Gujarati/Hindi layouts are visually tested;
- accessibility basics are verified.

## Evaluation

- baseline is independently runnable;
- final is independently runnable;
- same frozen cases are used;
- primary and safety metrics are reported;
- at least one challenging case is explained;
- run configuration/provider/model/prompt/corpus versions are captured.

## Hackathon artifacts

- improvement changelog complete;
- reproduction guide complete;
- representative trajectories complete;
- five-minute video follows the planned story;
- main failure mode and practical insight are explicitly stated.

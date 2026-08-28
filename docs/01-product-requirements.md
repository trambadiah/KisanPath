# Product Requirements

## Product name

**KisanPath** - a multilingual voice-first assistant for discovering and understanding agricultural government schemes.

## Primary user

A farmer who knows their own situation and need but may not know scheme names, eligibility terminology, or where to search.

## Core user job

> "Given my farm, location, crop, and need, tell me which government schemes may be relevant, what published conditions I appear to meet, what information is still missing, what documents I may need, and show me the evidence in language I understand."

## Product principles

- Ask only useful questions.
- Never hide uncertainty.
- Prefer short conversational explanations, with details available on demand.
- Make source evidence easy to inspect.
- Treat voice as first-class, especially on mobile.
- Never claim official approval or guaranteed eligibility.
- Do not request unnecessary sensitive identity data.

## Core journey

1. Farmer chooses/speaks preferred language.
2. Farmer describes their need naturally by voice or text.
3. KisanPath extracts a structured profile.
4. Critical or uncertain values are confirmed.
5. The system asks only missing questions that materially affect discovery or eligibility.
6. Candidate schemes are retrieved.
7. Eligibility rules are evaluated one by one.
8. Unknown conditions are surfaced explicitly.
9. Evidence verifier checks important claims.
10. Farmer receives a ranked result in their language with voice playback.
11. Farmer can inspect "Why this scheme?", documents, conditions, and official source references.

## Core statuses

### Likely eligible
The known farmer facts satisfy the published conditions available in the reviewed corpus, with no known deterministic failure. This is not official approval.

### Not eligible
At least one required deterministic condition clearly fails according to the known profile and reviewed rule.

### Insufficient information
One or more required conditions cannot be evaluated because necessary farmer information is missing.

### Manual review
The condition is ambiguous, non-structurable, conflicting, or not safe to decide automatically.

## MVP capabilities

- Gujarati, Hindi, English text interaction.
- Push-to-talk voice input and TTS response.
- Farmer profile extraction and confirmation.
- Gujarat plus selected central schemes.
- Hybrid scheme discovery.
- Condition-by-condition eligibility assessment.
- Evidence/provenance display.
- Document checklist.
- Conversation history within the current session.
- Evaluation dashboard/demo mode for judges/developers.

## Out of scope for MVP

- application submission;
- payment initiation;
- loan approval decisions;
- legal advice;
- storing Aadhaar;
- nationwide exhaustive scheme coverage;
- autonomous ingestion of unreviewed live web data into trusted eligibility rules.

## Key UX requirements

- mobile usable with one hand;
- obvious microphone state;
- transcript displayed after voice input;
- correction path before critical data is committed;
- no more clarification questions than necessary;
- evidence and eligibility conditions are readable without technical jargon;
- Gujarati/Hindi text must wrap correctly and retain visual hierarchy;
- every loading state explains what the system is doing at a high level without exposing hidden reasoning.

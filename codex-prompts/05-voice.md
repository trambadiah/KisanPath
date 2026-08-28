# Codex Prompt - Voice

Read AGENTS.md and docs/04-agent-workflow.md.

Implement provider-independent STT and TTS interfaces, then add one configurable provider implementation for each behind the interfaces. Make the architecture ready for additional vendors/local providers.

Voice input must enter the same canonical conversation workflow as typed input.

Critical fields extracted from ASR must preserve confidence/provenance and support explicit confirmation. Add tests for a simulated 3-vs-30-acre transcription ambiguity and an ambiguous regional land unit.

# Voice Abstraction and Canonical Workflow

KisanPath exposes provider-independent asynchronous STT and TTS ports under
`backend/src/kisanpath/voice/`. The first concrete adapters use OpenAI, while
configuration and registries allow additional cloud or local implementations without
changing domain, agent, or workflow code.

## Dependency boundary

```text
VoiceEligibilityWorkflow
  -> STTClient / TTSClient protocols
  -> STTRegistry / TTSRegistry
  -> voice/{stt,tts}/providers/openai.py
  -> provider SDK

transcript
  -> TextMessage
  -> TextEligibilityWorkflow
  -> canonical ConversationState
```

Only modules below `voice/stt/providers/` and `voice/tts/providers/` may import a
voice vendor SDK. Provider responses are converted immediately to canonical Pydantic
models, and provider exceptions are mapped to the KisanPath `VoiceError` hierarchy.

## Canonical contracts

`TranscriptionRequest` contains bounded audio bytes, filename, media type, optional
language hint and prompt, and a request ID. `TranscriptionResult` contains normalized
text, language, confidence, segments, explicit ambiguities/alternatives, provider and
model provenance, and latency.

`SynthesisRequest` contains localized text, language, optional voice/format/speed and
request ID. `SynthesisResult` contains bytes and explicit media type, format, provider,
model, voice, and latency. SDK objects never cross either boundary.

## Critical ASR facts and confirmation

The voice workflow converts the transcript to the same `TextMessage` accepted by the
typed workflow and supplies a trusted `ProfileMergeContext`. For every extracted fact,
the deterministic merger records:

- input modality, provider, and model;
- transcript/segment confidence;
- source segment IDs and ambiguity IDs;
- the original source message and the later confirmation message.

Critical facts such as state, district, and land area stop at `CONFIRM_VALUE` when the
effective confidence is below threshold or the matched ASR span has alternatives.
Voice-derived regional land units such as `bigha` also require confirmation and remain
un-normalized until reviewed geographic conversion data is available. A confirmation
turn retains the original voice provenance; it does not replace it with plain text
provenance.

## Configuration

Copy `backend/examples/voice.example.toml` and set only the environment variable named
by `api_key_env`. Secret values are rejected in typed provider settings.

```bash
export OPENAI_API_KEY=...
export KISANPATH_VOICE_CONFIG=backend/examples/voice.example.toml
```

Non-secret runtime overrides are `STT_PROVIDER`, `STT_MODEL`, `TTS_PROVIDER`,
`TTS_MODEL`, and `TTS_VOICE`.

```python
voice_workflow = VoiceEligibilityWorkflow(
    stt=stt_client,
    tts=tts_client,
    conversation=text_workflow,
)
result = await voice_workflow.handle_audio(
    "conversation-001",
    VoiceMessage(message_id="voice-001", audio=canonical_audio),
)
```

`backend/examples/voice_usage.py` demonstrates adapter construction, transcription,
and synthesis.

## Adapter capability matrix

| Adapter | STT language hint | STT confidence | STT timestamps | STT alternatives | TTS formats | Voice/speed | TTS instructions |
|---|---:|---:|---:|---:|---|---:|---:|
| OpenAI | Yes | Token logprobs when enabled | No in current JSON contract | No | MP3, Opus, AAC, FLAC, WAV, PCM | Yes | Model-dependent |

The canonical models support timestamps and alternatives even though the initial
OpenAI adapter does not manufacture unavailable alternatives. Future adapters can
advertise these capabilities and populate the same models through registry entries.

## Tests

Mocked adapter contract tests run without credentials. Deterministic tests cover a
simulated `3` versus `30` acre ASR ambiguity, a regional `bigha` unit, provider error
normalization, environment-only secrets, and a Gujarati voice turn entering the
canonical state machine. No fixture contains real farmer PII.

The live OpenAI TTS-to-STT round trip is opt-in and skips cleanly unless both
`KISANPATH_RUN_LIVE_VOICE_TESTS=1` and `OPENAI_API_KEY` are set.

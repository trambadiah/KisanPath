# Frontend Design System - Premium Voice-First Agritech

## Creative direction

KisanPath should feel like a premium AI product built for agriculture, not like a government portal and not like a template with green buttons and farm stock photos.

The visual language should combine:

- deep midnight/charcoal surfaces;
- refined emerald and jade accents;
- restrained warm saffron/copper highlights for important moments;
- soft frosted layers and subtle depth;
- crisp typography with excellent Indic-script rendering;
- understated topographic/field-line texture;
- elegant waveform/microphone motion;
- evidence cards that feel precise and trustworthy.

Avoid:

- neon-green agriculture clichés;
- cartoon crops/tractors;
- excessive gradients;
- noisy glassmorphism everywhere;
- huge dashboard grids as the primary experience;
- animation that slows task completion;
- eligibility state communicated by color alone.

## Suggested palette tokens

Use semantic tokens rather than hardcoded colors inside components. One possible direction:

```text
canvas            near-black midnight
surface-1         deep graphite
surface-2         lifted charcoal
surface-glass     translucent dark layer
text-primary      warm off-white
text-secondary    cool muted gray
brand             refined emerald
brand-soft        muted jade
accent-warm       restrained saffron/copper
success           accessible green
warning           accessible amber
error             accessible coral/red
divider           subtle cool border
```

Exact values should be validated for WCAG contrast.

## Typography

Use one high-quality Latin UI family plus a compatible Indic family with similar proportions, or a family supporting Gujarati/Devanagari well. Test real Gujarati and Hindi strings, not placeholder Latin transliterations.

Hierarchy:

- display: confident but not oversized;
- section title: compact and sharp;
- body: highly readable on low-cost mobile screens;
- metadata: smaller but never low-contrast;
- numeric eligibility facts: tabular digits where useful.

## Layout philosophy

### Desktop
Centered assistant workspace with contextual side panels rather than a dense admin dashboard.

### Mobile
Single-column conversational flow. Bottom-mounted voice control should remain reachable with one thumb while respecting safe areas.

## Signature visual: KisanPath voice orb

The primary assistant screen should have a refined voice control/orb:

- idle: subtle halo/breath;
- listening: responsive waveform/radial energy;
- processing: controlled orbit/progress motion;
- speaking: softer synchronized pulse;
- error: stable icon + clear action, not frantic animation.

Respect `prefers-reduced-motion`.

## Core screens

### 1. Landing
Purpose: communicate value instantly.

Recommended composition:

```text
minimal nav
premium hero statement
voice demo CTA + text fallback
3-step "Speak -> Check -> Understand" flow
small trust/evidence section
sample result preview
privacy/safety note
```

Do not lead with a feature grid.

### 2. Assistant
Primary product screen.

```text
header with language + session status
conversation transcript
large voice control
profile chips for confirmed facts
inline clarification/confirmation cards
progress text: "Checking published eligibility conditions..."
```

Profile chips should communicate confirmed vs needs-confirmation states without making the screen feel like a form.

### 3. Recommendation result
Top section:

```text
"3 schemes may match your situation"
small explanation of non-official status
```

Each scheme card:

- scheme name;
- fit/status badge + icon/text;
- one-line benefit summary;
- condition summary e.g. `5 passed / 1 needs information`;
- next missing action;
- "Why this?";
- evidence/source indicator;
- listen button.

Cards should feel like premium financial/product cards rather than generic accordions.

### 4. Scheme detail / evidence drawer
Use a split detail view on desktop and bottom sheet/full page on mobile.

Sections:

- why it matched;
- eligibility conditions;
- unknown/manual-review conditions;
- documents;
- application guidance;
- source provenance.

### 5. Profile confirmation sheet
Show only values relevant to the current decision. Let users correct a transcript-derived value quickly.

### 6. Judge/developer evaluation page
Separate from farmer UI. Show baseline vs final metrics, case explorer, and sanitized trajectory links with a restrained technical aesthetic.

## Eligibility status components

Do not use binary "Eligible / Ineligible" as the only language.

Recommended:

```text
Likely eligible
Not eligible based on published condition
Need more information
Manual review recommended
```

Each status uses icon + label + short explanation.

## Motion

Use motion to clarify state:

- card transitions when results arrive;
- profile chip confirmation;
- voice waveform;
- evidence drawer;
- subtle count-up on evaluation metrics.

No decorative continuous animation except extremely subtle ambient elements.

## Imagery

Prefer:

- abstract field/topographic line motifs;
- tasteful macro agricultural textures used sparingly;
- real interface content;
- custom iconography.

If people imagery is used, it must feel authentic and respectful; avoid making the UI dependent on stock-photo hero banners.

## Accessibility

- WCAG AA contrast minimum;
- visible keyboard focus;
- 44px+ touch targets where appropriate;
- screen-reader labels for voice controls;
- transcript always available as alternative to audio;
- no important information encoded only in motion, audio, or color;
- reduced-motion mode;
- localized aria labels;
- support text scaling without clipping.

## Frontend component inventory

```text
AppShell
LanguageSwitcher
VoiceOrb
VoiceRecorder
TranscriptBubble
AssistantMessage
FarmerMessage
ProfileFactChip
ProfileConfirmationCard
ClarificationCard
WorkflowProgress
SchemeRecommendationCard
EligibilityStatusBadge
RuleChecklist
EvidenceSourceChip
EvidenceDrawer
DocumentChecklist
ListenButton
EmptyState
ErrorState
SkeletonState
MetricComparisonCard
TrajectoryViewer
```

## Premium quality bar

Before calling a screen finished, ask:

- Does it look intentional at 390px width?
- Does Gujarati look as polished as English?
- Is the main action obvious within two seconds?
- Are evidence and uncertainty visually clearer than decorative elements?
- Are loading and error states as polished as the happy path?
- Would this still look premium without stock photography?

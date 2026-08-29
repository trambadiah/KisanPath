# Frontend

KisanPath's frontend is a Next.js 16 App Router application with a custom, premium,
mobile-first voice assistant experience. It uses strict TypeScript boundaries, local
Indic font assets, semantic HTML, and a small CSS design system rather than a generic
dashboard template.

The design direction is defined in `../docs/08-frontend-design-system.md`.

The frontend is not a generic dashboard. The core experience should feel like a refined consumer-grade assistant with clear evidence and eligibility cards layered underneath.

## Routes

- `/` — voice-first landing page and evidence-backed result preview;
- `/assistant` — canonical voice/text conversation, profile facts, and confirmation;
- `/schemes` — recommendation result flow;
- `/schemes/[id]` — full evidence and document detail;
- `/demo/evaluation` — frozen baseline/final evaluation explorer;
- `/privacy` — concise farmer-facing privacy and safety guidance.

## Data boundary

All product views depend on `KisanPathClient` in `lib/contracts.ts`. The HTTP adapter
uses the versioned endpoints from `docs/07-api-contract.md`. When
`NEXT_PUBLIC_KISANPATH_API_URL` is unset, `SeededKisanPathClient` provides explicitly
labelled fictional, reviewed demo content. Removing the seed adapter does not require
changing page or component contracts.

## Local development

```bash
npm install
npm run dev
```

Verification:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

The voice recorder uses the browser `MediaRecorder` API. Microphone errors preserve
the current profile and keep typed input available. All important information remains
visible as text, and motion is disabled through `prefers-reduced-motion`.

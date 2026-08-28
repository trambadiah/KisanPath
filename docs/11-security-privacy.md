# Security, Privacy, and Safety

## Data minimization

Do not request or store identity data unless the feature genuinely requires it. The initial product should not request Aadhaar or bank credentials.

Prefer the minimum profile needed for scheme discovery/eligibility:

- state/district;
- landholding;
- crop/activity;
- ownership/tenancy where relevant;
- irrigation;
- farmer category where relevant;
- stated need.

## Consequential-action boundary

KisanPath is an assistance and explanation system. It does not submit applications, move money, sign documents, or make official government decisions.

## Human-review boundary

Rules tagged manual review, conflicting source information, or low-confidence semantic interpretations must remain visibly unresolved.

## Prompt injection

Treat source documents and user-provided content as untrusted data, not instructions. Retrieval content must be wrapped/marked as evidence. Provider prompts must state that instructions embedded in evidence are not executable commands.

## Secrets

- environment/secret manager only;
- no secrets in URLs or logs;
- redact authorization headers;
- `.env` is ignored;
- provide only `.env.example`.

## API controls

- request-size limits;
- audio duration/size limits;
- rate limiting;
- auth for admin operations;
- RBAC for corpus publishing;
- CSRF/session protection as appropriate;
- strict CORS configuration;
- secure headers;
- validated file types.

## Audit

Record security-relevant events such as:

- scheme publication;
- rule edits;
- admin actions;
- provider configuration changes;
- evaluation corpus changes;
- workflow manual-review decisions.

Audit events should record actor/action/target/metadata without secret values.

# LocalPDF implementation notes

- Follow `DECISIONS.md`, `PROJECT_SPEC.md`, and `ACCEPTANCE_CRITERIA.md`.
- Keep originals immutable and publish every derived file as a new hashed version.
- Never send document bytes to a remote service and never add telemetry.
- Do not use shell interpolation for document-processing subprocesses.
- Signature-lite must always be described as low-risk consent/hash sealing, not a qualified signature.


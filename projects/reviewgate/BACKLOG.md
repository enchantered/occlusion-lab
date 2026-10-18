# ReviewGate: next useful increments

## Before a real-customer pilot

1. Validate the buyer and recurring review problem with 10–15 interviews; secure at least two paid pilot commitments before expanding scope. No outreach is authorized by this repository alone.
2. Add authenticated reviewer identity and authorization. A reviewer name supplied on the command line is an assertion, not identity verification.
3. POSIX owner-only new database/directory modes and unsafe-path rejection are implemented and tested. Still add retention/deletion policy and encrypted backups as required by pilot agreements. SQLite draft text remains plaintext; trusted parent directories are required.
4. Add an externally anchored or signed audit checkpoint. A local hash chain can detect many mutations but cannot prove integrity if an attacker rewrites the entire database or removes a fully consistent tail. Do not call it immutable.
5. Add document-level data classification and expert-reviewed redaction evaluations. Regex masking misses names, account numbers and context-specific sensitive information. It can also mask harmless text. Never use its output as proof that a source is safe to transmit.
6. Real Runner/typed-output compatibility with pinned SDK 0.24.0 now passes using an offline synthetic model with socket connections forbidden. Still run a real provider only after explicit data-transfer permission and a budget, and validate quality with a representative, consented evaluation set. Offline compatibility is not live provider validation.

## Next product experiments, only after validation

- A narrow review interface with draft diffs and reviewer comments; no client messaging.
- Versioned edits that always create a new pending draft and invalidate prior approval.
- One read-only document integration with scoped access and revocation tests.
- Run concurrency, crash-recovery and large-input tests before multi-user use.

## Definition of a quality maintenance commit

A maintenance change must resolve a reproducible bug, add a test that catches a real regression, improve a documented security boundary, or implement an evidence-backed backlog item. Record the reason, failing-before/passing-after evidence where applicable, and remaining limits. Do not create cosmetic churn simply to maintain a daily streak.

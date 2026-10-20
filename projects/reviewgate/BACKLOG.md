# ReviewGate: next useful increments

## Before a real-customer pilot

1. Validate the buyer and recurring review problem with 10–15 interviews; secure at least two paid pilot commitments before expanding scope. No outreach is authorized by this repository alone.
2. Add authenticated reviewer identity and authorization. A reviewer name supplied on the command line is an assertion, not identity verification.
3. POSIX owner-only new database/directory modes and unsafe-path rejection are implemented and tested. Still add retention/deletion policy and encrypted backups as required by pilot agreements. SQLite draft text remains plaintext; trusted parent directories are required.
4. Portable checkpoint creation and opt-in audit/export verification compare the current history with a separately retained trusted witness, including after valid appends. `export --checkpoint` checks that witness and the approved draft in one read snapshot. Still add an externally anchored or signed checkpoint service and protected retention. Nothing automatically uploads or protects the witness, and ordinary export without the flag does not require it. Replacing both database and witness still defeats the check; do not call the log immutable.
5. Add document-level data classification and expert-reviewed redaction evaluations. Regex masking misses names, account numbers and context-specific sensitive information. It can also mask harmless text. Never use its output as proof that a source is safe to transmit.
6. Real Runner/typed-output compatibility with pinned SDK 0.24.0 now passes using an offline synthetic model with socket connections forbidden. Still run a real provider only after explicit data-transfer permission and a budget, and validate quality with a representative, consented evaluation set. Offline compatibility is not live provider validation.

## Next product experiments, only after validation

- A narrow review interface with draft diffs and reviewer comments; no client messaging.
- Versioned edits that always create a new pending draft and invalidate prior approval.
- One read-only document integration with scoped access and revocation tests.
- Competing approvals and approve-versus-reject now have bounded, barrier-based regression tests proving one terminal winner. Fault injection verifies transactional rollback after draft insertion or approval update if audit append fails. Still run multi-process stress, OS crash/power-loss recovery and large-input tests before multi-user use; exception rollback is not proof of power-loss durability.

## Definition of a quality maintenance commit

A maintenance change must resolve a reproducible bug, add a test that catches a real regression, improve a documented security boundary, or implement an evidence-backed backlog item. Record the reason, failing-before/passing-after evidence where applicable, and remaining limits. Do not create cosmetic churn simply to maintain a daily streak.

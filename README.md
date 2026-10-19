# Agentic Venture Lab

Evidence-led daily MVP experiments, with tests and substantive incremental maintenance. The first experiment is **ReviewGate**, a local-first approval workflow for AI-assisted client briefs at small professional-services firms.

GitHub account: `enchantered`. Private repository creation was denied by the connector's `CreateRepository` permission on October 18. The existing `enchantered/ProjectAdi` repository is public and empty; its connector-authenticated Git push again returned HTTP 403 on 2026-10-19. No code was published and no repository visibility was changed. This workspace is a local Git repository; do not treat it as published until a successful remote push is verified. The Cue coordinator owns the daily schedule. This project creates no recurring task or scheduled GitHub Action.

## Run the first experiment

Python 3.11+ is sufficient for the offline core. No API key or package installation is required.

```bash
python -m unittest discover -s tests -v
python -m venturelab rank research/2026-10-17-opportunities.json
python -m projects.reviewgate demo projects/reviewgate/sample.json --db artifacts/review.sqlite
```

The demo returns an `id`, `hash`, and `pending` status. It does not approve or export anything. Inspect the local draft, then deliberately approve that exact version using the returned values:

```bash
python -m projects.reviewgate inspect DRAFT_ID --db artifacts/review.sqlite
python -m projects.reviewgate approve DRAFT_ID --hash DRAFT_HASH --reviewer 'Your name' --db artifacts/review.sqlite
python -m projects.reviewgate export DRAFT_ID --db artifacts/review.sqlite
python -m projects.reviewgate audit --db artifacts/review.sqlite
```

On POSIX systems, new database files are created with owner-only permissions (0600), and newly created parent directories use 0700. Existing parent directories are not changed. Symlink/special-file database paths and existing files with group/other permission bits are rejected before opening. If an older database is rejected, inspect the path and deliberately set its permissions to 0600 before reopening; the application does not silently chmod user files. Keep the parent directory trusted. These initialization checks do not prevent later replacement by the same user, encrypt plaintext, authenticate reviewers, or protect backups.

Inspection displays pending text locally for review; it is not approved delivery. To decline a draft, run `python -m projects.reviewgate reject DRAFT_ID --reason 'Needs revision' --db artifacts/review.sqlite`. Export prints JSON locally; it does not send a client message. Unapproved/rejected drafts and detected state/audit corruption cannot be exported. Repeated approval is an error; repeated export is read-only. Changes require a new pending draft.

```bash
python -m projects.reviewgate redact path/to/synthetic-source.txt
```

Redaction returns masked text and finding types/offsets, without returning the raw matched values. It is heuristic and does not reliably remove all personal or confidential information.

## Detect rollback against a trusted checkpoint

The ordinary audit validates internal consistency, so restoring an older, consistent database can pass. A checkpoint records the verified nonempty history's event count and head hash, without draft text. Retain its JSON in a separate trusted location, then verify that the database still contains that exact history prefix:

```bash
python -m projects.reviewgate checkpoint --db artifacts/review.sqlite
# Retain the printed JSON separately; the commands do not upload or protect it.
python -m projects.reviewgate audit --db artifacts/review.sqlite --checkpoint /path/to/trusted-checkpoint.json
```

Later valid events may be appended. A rollback before the checkpoint, a different history, or internal corruption fails verification. Exit status is 0 for a match, 1 for a validly formed witness that does not match, and 2 for an invalid/unreadable witness or command error. Checkpoint files are limited to 4 KB. Empty databases cannot issue a meaningful checkpoint.

This is opt-in audit verification, not an automatic export gate, signature, timestamp service or external anchoring integration. It only adds evidence if the retained checkpoint itself is trusted and protected separately. Replacing both the database and witness defeats it, and changes after a successful audit need another check. It does not authenticate reviewer identity or encrypt data.

## Optional agent-generated drafts

The adapter uses OpenAI Python Agents SDK 0.24.0, pinned in `requirements-agent.in`. It uses a typed output, no action tools, disabled tracing, a two-turn limit, and a 900-output-token setting. The chosen model must support the requested settings. Actual SDK Runner and typed-output parsing now pass tests with a synthetic offline model; this is not live provider validation.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-agent.lock
# Configure provider credentials securely in the execution environment.
# Use synthetic text until real-data handling is independently approved.
.venv/bin/python -m projects.reviewgate.agent_adapter synthetic-source.txt \
  --db artifacts/review.sqlite --model YOUR_EXPLICIT_MODEL --allow-network
```

Without `--allow-network`, the adapter refuses to send text. That flag authorizes transmission of the heuristically masked source to the configured model, not a privacy guarantee. Review the input and provider data-handling terms first. The adapter returns a draft ID: use `inspect` to review its text and uncertainties and obtain its exact approval hash. Generated drafts remain pending; the agent has no approval, export, email, refund or deployment tool. Token/turn limits do not enforce a monetary budget. No live model call was made during this initial build.

## Why this project

[The first decision](research/2026-10-17-decision.md) compares review controls, invoice exceptions and social-content approvals against opened demand reports. The [machine-readable shortlist](research/2026-10-17-opportunities.json) records evidence and subjective scores. ReviewGate's 64/100 versus invoice exceptions' 63/100 is a close analyst judgment, not a return forecast or statistical result. Research supports testing the problem, not calling the business investible.

The commercial gate is 10–15 buyer interviews and at least two paid pilot commitments before expanding. No outreach or paid pilot has happened. The evidence is U.S./OECD-oriented, not validated Indian demand.

## Daily continuation

Follow [AGENTS.md](AGENTS.md) on every coordinator-run execution. Research current sources, inspect active projects, implement one meaningful increment, run the tests, inspect the diff, then commit and push only to an authorized repository. Maintain older projects based on real defects and prioritized work; do not generate artificial activity commits. A new experiment may be declined if evidence is weak or critical maintenance takes priority.

The [2026-10-19 review](research/2026-10-19-decision.md) now places invoice exceptions first for discovery (67/100 versus ReviewGate 64/100 and subscription detection 46/100), based on newer 2026 late-payment evidence. This subjective lead is not an investment verdict or build authorization. ReviewGate remains the only active prototype: today's increments add trusted-checkpoint audit verification and transaction-safety regressions rather than another unvalidated product. The October 18 storage hardening and real-SDK offline tests remain in place.

The [project backlog](projects/reviewgate/BACKLOG.md) prioritizes identity, retention/encrypted backups, independently anchored audit evidence and real redaction evaluation before customer use. [Tooling notes](docs/AGENT_TOOLING.md) link the official SDK capabilities. CI defines core tests on Python 3.11, 3.12 and 3.13 plus an SDK compatibility job on push/PR only; remote CI has not run because publishing remains blocked. Local tests ran on Python 3.12.

## Important limitations

This is an engineering prototype, not a production compliance or data-loss-prevention product. SQLite contains plaintext drafts. Reviewer names are not authenticated. A local hash chain is not immutable and cannot prove integrity against a full database rewrite or consistent rollback; integrity checks currently replay the full history, so scaling requires further work. Source text is hashed rather than stored, but low-entropy source hashes can be guessed and generated drafts may repeat sensitive facts. Regex masking misses names, account identifiers and contextual secrets and can over-mask harmless text. Client confidentiality, security review, provider compatibility and willingness to pay remain unvalidated.

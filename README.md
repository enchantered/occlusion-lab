# Agentic Venture Lab

Evidence-led daily MVP experiments, with tests and substantive incremental maintenance. The first experiment is **ReviewGate**, a local-first approval workflow for AI-assisted client briefs at small professional-services firms.

GitHub account: `enchantered`. Remote creation was blocked by the connected account's `CreateRepository` permission. This workspace is a local Git repository; do not treat it as published until a successful remote push is verified. The Cue coordinator owns the daily schedule. This project creates no recurring task or scheduled GitHub Action.

## Run the first experiment

Python 3.11+ is sufficient for the offline core. No API key or package installation is required.

```bash
python -m unittest discover -s tests -v
python -m venturelab rank research/2026-10-17-opportunities.json
python -m projects.reviewgate demo projects/reviewgate/sample.json --db artifacts/review.sqlite
```

The demo returns an `id`, `hash`, and `pending` status. It does not approve or export anything. Read the sample draft, then deliberately approve that exact version using the returned values:

```bash
python -m projects.reviewgate approve DRAFT_ID --hash DRAFT_HASH --reviewer 'Your name' --db artifacts/review.sqlite
python -m projects.reviewgate export DRAFT_ID --db artifacts/review.sqlite
python -m projects.reviewgate audit --db artifacts/review.sqlite
```

Export prints JSON locally; it does not send a client message. Unapproved/rejected drafts and detected state/audit corruption cannot be exported. Repeated approval is an error; repeated export is read-only. Changes require a new pending draft.

```bash
python -m projects.reviewgate redact path/to/synthetic-source.txt
```

Redaction returns masked text and finding types/offsets, without returning the raw matched values. It is heuristic and does not reliably remove all personal or confidential information.

## Optional agent-generated drafts

The adapter uses the current verified OpenAI Python Agents SDK release, pinned in `requirements-agent.in`. It uses a typed output, no action tools, disabled tracing, a two-turn limit, and a 900-output-token setting. The chosen model must support the requested settings. Import/configuration checks are not live provider validation.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-agent.in
# Configure provider credentials securely in the execution environment.
# Use synthetic text until real-data handling is independently approved.
.venv/bin/python -m projects.reviewgate.agent_adapter synthetic-source.txt \
  --db artifacts/review.sqlite --model YOUR_EXPLICIT_MODEL --allow-network
```

Without `--allow-network`, the adapter refuses to send text. That flag authorizes transmission of the heuristically masked source to the configured model, not a privacy guarantee. Review the input and provider data-handling terms first. Generated drafts remain pending; no approval, export, email, refund or deployment tool is available. Token/turn limits do not enforce a monetary budget. No live model call was made during this initial build.

## Why this project

[The first decision](research/2026-10-17-decision.md) compares review controls, invoice exceptions and social-content approvals against opened demand reports. The [machine-readable shortlist](research/2026-10-17-opportunities.json) records evidence and subjective scores. ReviewGate's 64/100 versus invoice exceptions' 63/100 is a close analyst judgment, not a return forecast or statistical result. Research supports testing the problem, not calling the business investible.

The commercial gate is 10–15 buyer interviews and at least two paid pilot commitments before expanding. No outreach or paid pilot has happened. The evidence is U.S./OECD-oriented, not validated Indian demand.

## Daily continuation

Follow [AGENTS.md](AGENTS.md) on every coordinator-run execution. Research current sources, inspect active projects, implement one meaningful increment, run the tests, inspect the diff, then commit and push only to an authorized repository. Maintain older projects based on real defects and prioritized work; do not generate artificial activity commits. A new experiment may be declined if evidence is weak or critical maintenance takes priority.

The [project backlog](projects/reviewgate/BACKLOG.md) prioritizes identity, storage protection, independently anchored audit evidence and real redaction evaluation before customer use. [Tooling notes](docs/AGENT_TOOLING.md) link the official SDK capabilities. CI runs offline tests on Python 3.11, 3.12 and 3.13 on push/PR only; remote CI has not run until publishing succeeds.

## Important limitations

This is an engineering prototype, not a production compliance or data-loss-prevention product. SQLite contains plaintext drafts. Reviewer names are not authenticated. A local hash chain is not immutable and cannot prove integrity against a full database rewrite or consistent rollback; integrity checks currently replay the full history, so scaling requires further work. Source text is hashed rather than stored, but low-entropy source hashes can be guessed and generated drafts may repeat sensitive facts. Regex masking misses names, account identifiers and contextual secrets and can over-mask harmless text. Client confidentiality, security review, provider compatibility and willingness to pay remain unvalidated.

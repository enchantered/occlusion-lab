# Everyday AI and established tools: a living problem log

## 2026-10-19 — First baseline

**The strongest signal is coexistence, not wholesale replacement.** People increasingly use AI for everyday questions and tasks, but still return to reviews, saved text, search, and human judgment. Our opportunity is to improve those handoffs—not add AI to a workflow that already works. “Underserved” below means a problem worth testing; none is proven untouched or commercially viable.

This log starts the project's consumer-research history. The simulator is still a developer-facing spatial-reasoning demo, not an everyday consumer product. These findings guide future projects; they do not establish demand for Occlusion Lab.

### What has changed

| Evidence period | Observed behavior | What it does—and does not—tell us |
| --- | --- | --- |
| 2025 to July 2026 | Menlo Ventures reports U.S. adult AI use rising from 61% to 64%, and daily use from 19% to 25%. | More frequent use grew faster than reach in its survey. Its July 2026 Morning Consult sample covers 5,067 U.S. adults; the April 2025 wave covered 5,031. This is self-report and an investor-published study, not independent usage telemetry. [Report, published September 16, 2026](https://menlovc.com/perspective/2026-the-state-of-consumer-ai/). |
| February 2026 | Pew reports 49% of U.S. adults had ever used AI chatbots. | Pew surveyed 5,119 U.S. adults, February 17–23. Its chatbot wording is narrower than Menlo's AI measure: do not combine these figures into a single trend. Its historical comparison also has a question-universe caveat. [Pew, June 17, 2026](https://www.pewresearch.org/internet/2026/06/17/americans-and-ai-2026-chatbots-smart-devices-and-views-on-impact/). |
| 2025 consumer ChatGPT activity | OpenAI reports roughly 70% non-work usage; practical guidance, information-seeking and writing together account for about three-quarters of conversations. | Everyday utility is not confined to work. The analysis covers 1.5 million consumer-plan conversations from one provider; it does not measure adoption or the whole AI market. [OpenAI, September 15, 2025](https://openai.com/index/how-people-are-using-chatgpt/). |
| 2026 local-business research | BrightLocal reports 45% used AI for local recommendations, while Google-review use remained 71%. It reports 59% check review profiles beyond AI summaries, versus 23% relying on the summary alone. | AI and established review workflows coexist. Representative panel: 1,002 U.S. adults via SurveyMonkey; AI-user cuts use 455 respondents. These are different activities, not exclusive market shares or proof AI caused review use to change. [BrightLocal's 2026 research](https://www.brightlocal.com/research/lcrs-ai-trust/). |

**Geography gap:** these figures mostly describe the United States, not India or the world. Future runs should add India-specific, multilingual, mobile-first and lower-connectivity evidence before choosing a general-public target. Do not relabel U.S. results as global behavior.

### Recurring friction and ideas to test

**1. Finding an answer again, after the conversation disappears into history.** In an [October 5, 2025 Hacker News discussion](https://news.ycombinator.com/item?id=45478654), people describe starting again rather than retrieving old answers, renaming a few long-running chats, and saving useful text elsewhere. A separate [June 2026 OpenAI community report](https://community.openai.com/t/issues-about-chat-history-search/1383159) describes irrelevant history-search results on web and Android. These are anecdotes, not prevalence estimates or proof a reported bug remains unresolved.

- **Established workaround:** copy important text into notes or files, manually rename chats, or re-ask the question.
- **Candidate:** a local, read-only conversation library that imports user-provided exports, searches exact text, and links results to their original context. No account credentials or cloud upload by default.
- **Existing solution check:** [ChatGPT already offers data export](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data); current guidance says preparation can take up to seven days, download links expire after 24 hours, and exports cannot restore deleted chats. The opportunity is retrieval and usability after authorized export—not inventing export or promising recovery.
- **Next validation:** compare existing search/export tools; ask five consenting users to retrieve a known answer using their usual method and a prototype. Measure success and time, and verify source text is preserved. Use synthetic data in public examples.

**2. Checking an AI recommendation without repeating the whole search.** BrightLocal's summary-to-review behavior above supports a handoff problem. It does not prove existing apps fail to address it.

- **Established workaround:** reopen review sites and search results, check dates, compare conflicting details.
- **Candidate:** an evidence card that keeps each recommendation beside its source links, retrieval date, conflicting claims and a user checklist. Missing information stays marked unknown; a link alone is not verification.
- **Next validation:** inspect existing browser, notes and research products, then test ten ordinary local-search tasks. Measure supported claims, stale details and verification time. Do not automate purchases or endorse sensitive medical/financial advice.

**3. Knowing what an assistant will change before it acts.** Menlo's 2026 report places accuracy (45%), trustworthiness (40%), and security/privacy (36%) ahead of ease of use (32%) among AI users' priorities. This supports trust as a design consideration—not a demonstrated demand for one new product.

- **Established workaround:** complete the action manually or inspect every step.
- **Candidate:** a plain-language action receipt showing proposed changes, required permissions, approval, outcome and any available undo. Do not claim an irreversible action can be undone.
- **Next validation:** review existing approval and audit features; test whether users can correctly identify the action and its consequences before approval. Keep early prototypes local and simulated.

### What this means for Occlusion Lab

Its useful transferable principle is **unknown is not confirmed free**: the planner cannot silently use hidden ground truth. Likewise, future consumer tools should not treat absent evidence as permission, a verified claim, or a completed action. This is a design analogy, not consumer validation or an ML capability claim.

The [Godot navigation discussion](https://forum.godotengine.org/t/obstacles-in-pathfinding-do-not-work/59417), opened in May 2024 with further replies in January 2026, illustrates persistent confusion between pathfinding and obstacle avoidance. [ROS2 mapping troubleshooting](https://github.com/hermanumrao/ROS2_pcd_to_occupancy_grid/blob/main/README.md) distinguishes sparse/unknown maps from noisy maps. These explain the educational demo's context, not general-public demand.

### How future runs extend this log

Append a new dated section; preserve earlier evidence and record corrections explicitly. Each entry should capture:

1. The user's daily task, AI tool, established alternative and actual workaround.
2. Source URL, publication/observation date, geography, population, and whether evidence is a survey, telemetry, or an anecdote. Read the source, not just its search snippet.
3. Whether the issue recurs independently, what existing products already solve, and what remains unverified. Never call a market untouched without a competitor check.
4. One small proposed improvement, success measure, privacy constraints and a decision: investigate, prototype, maintain, or reject.
5. For maintained projects: reproducible bugs, tests run, changes shipped, setup/troubleshooting updates and known limitations. Explain behavior changes to non-experts.

Reverse-engineer workflows and publicly documented interfaces, not proprietary code or private data. Use original implementations, user-authorized imports and licensed assets. Keep releases private unless public publication is explicitly authorized; before a public release, settle licensing and provide beginner setup, examples, accessibility checks, troubleshooting and release notes.

**Operational status:** this entry does not enable monitoring, create a schedule, reactivate daily work, or make the repository public. The existing daily schedule remains paused pending coordinator action.

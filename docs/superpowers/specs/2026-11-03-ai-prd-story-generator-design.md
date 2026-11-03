# AI PRD & User Story Generator — Design Spec

Date: 2026-11-03 · Status: draft for review

## 1. Purpose and success criteria

**Purpose.** A portfolio repository (GitHub + CV) for a Product Owner job search. It shows command of product specification (PRD, INVEST, Gherkin/BDD) and practical use of AI to cut the time spent writing specs.

**Audience.** Recruiters and product leaders. Many will not run the app, so the README, real example outputs and a demo GIF weigh more than the code.

**Success criteria**
- A visitor can see a full result in under a minute with no API key (demo mode).
- The pipeline turns a free-text feature idea into: PRD, epics + user stories, INVEST review (with rewrites of weak stories), Gherkin acceptance criteria, and import-ready CSVs for Azure DevOps and Jira.
- The prompts are readable, versioned artifacts that show PO reasoning.
- Project costs the author nothing to host or demo.
- Bilingual: PT-BR and EN (README, prompts, UI output language).

**Out of scope for v1 (roadmap):** clarifying-interview step, direct Azure DevOps/Jira API integration, version history.

## 2. Key decisions

| Decision | Choice | Why |
|---|---|---|
| Core approach | Multi-step pipeline with INVEST reviewer | Shows PO process; each prompt is a readable artifact |
| Providers | Pluggable, BYOK: Gemini, Groq (free tiers), Claude, OpenAI | Zero cost for author and visitors; shows architecture sense |
| No-key access | Demo mode reading pre-generated examples | Recruiter sees results instantly |
| Language | Bilingual PT-BR / EN | Covers Brazilian and international markets |
| Output format from LLM | JSON validated by `models.py`, 1 retry | Reliable exports |
| UI | Single-page Streamlit | Smallest thing that demos well |

## 3. Repository structure

```
ai-prd-story-generator/
├── README.md              # EN
├── README.pt-BR.md
├── LICENSE                # MIT
├── requirements.txt
├── .env.example
├── app.py                 # Streamlit UI only
├── prompts/
│   ├── pt-BR/ 01_prd.md 02_stories.md 03_invest_review.md 04_gherkin.md
│   └── en/    (same four files)
├── src/
│   ├── providers.py       # LLM interface + Gemini, Groq, Claude, OpenAI
│   ├── pipeline.py        # orchestrates the 4 steps
│   ├── models.py          # PRD, Story, Review (validated)
│   └── exporters.py       # Azure DevOps CSV, Jira CSV, Markdown
├── examples/              # 2 full cases (input → PRD → stories → CSV)
├── docs/
│   ├── prompt-design.md
│   ├── import-guide.md / import-guide.pt-BR.md
│   └── (demo GIF / screenshots)
├── tests/
└── .github/workflows/     # pytest on push
```

Boundaries: the UI does not know providers; the pipeline does not know Streamlit; exporters receive only models; prompts are data in `.md` files.

## 4. Data flow

```
idea + language + provider/key
  → [1] PRD (JSON → Markdown)
  → [2] epics + stories (As a / I want / So that, MoSCoW, estimate, prd_ref)
  → [3] INVEST review (score 0–2 per criterion, verdict, rewrite if any < 2)
  → [4] Gherkin (2–4 scenarios per story: happy, alternative, error)
  → exporters: PRD.md · azure_devops.csv · jira.csv
```

Each step receives only what it needs. Step 2 consumes the PRD, not the raw idea. Stories carry `prd_ref` for traceability.

## 5. Prompt engineering

- Explicit personas: senior PM (PRD), critical PO (reviewer — adversarial by design).
- Fixed JSON output schema described in the prompt, with few-shot examples (one good story, one bad).
- Objective INVEST rubric: each criterion has a definition and a test (e.g. Small: estimate above 8 points scores 0).
- Gherkin rules: one behaviour per scenario, business language, scenario names state the rule. PT-BR uses localized keywords (Dado/Quando/Então), EN uses Given/When/Then.
- Anti-invention: anything not derived from the idea is marked as an assumption; PRD has an assumptions and open-questions section; no invented metrics.
- Language is selected by prompt folder (`pt-BR` or `en`).

## 6. Exporters

- **Azure DevOps:** CSV with `Work Item Type, Title 1, Title 2, Description, Acceptance Criteria, Priority, Story Points, Tags`. Epic uses `Title 1`, user story uses `Title 2`, giving the parent/child hierarchy. Final column set to be verified against current Azure DevOps docs during implementation.
- **Jira:** CSV with `Issue Type, Summary, Description, Priority, Epic link/Parent, Labels`; acceptance criteria inside the description. The epic-to-story linkage differs between company-managed and team-managed projects; verify against current Jira docs during implementation.
- **Markdown:** the full PRD.
- UTF-8 with correct escaping of accents, commas and line breaks.

## 7. Error handling

- Invalid JSON: one retry with the validation error appended; second failure shows a clear error.
- API failure or rate limit (common on free tiers): clear message; outputs of earlier steps stay visible.

## 8. User interface

Single Streamlit page.
- **Sidebar:** language, provider, API key (password field), model (sensible default), demo-mode toggle (disables provider and key).
- **Main:** idea text box with two clickable examples ("customer referral program", "abandoned cart recovery"), **Generate** button.
- **Results tabs:** PRD · Stories (INVEST scores before/after rewrite) · Gherkin · Export (three downloads + link to import guide).
- Progress via `st.status`; each step's result appears as soon as it is ready.
- Demo mode replays `examples/` with simulated step progress and no network.
- Privacy: key kept only in `st.session_state`; no content logging; on-screen notice that the idea is sent to the chosen provider.

## 9. Import guides (docs/)

Two guides (EN and PT-BR), written during implementation and checked against the real CSVs the app generates and the official docs.

- **Azure DevOps:** prerequisites (edit work items, process Agile/Scrum/Basic) → generate CSV → Boards → Work items → Import Work Items → review preview → Save items; hierarchy via `Title 1`/`Title 2`; troubleshooting (UTF-8, unknown work item type, required fields, column names).
- **Jira (Cloud):** prerequisites (admin permission, project exists) → generate CSV → Settings → System → Import and export → External System Import → CSV → map columns and save mapping; epic linkage differences; troubleshooting (delimiter, date format, priorities missing in project).

## 10. Testing

pytest, no network, no cost.
- Pipeline with a fake provider: step order, PRD propagation, earlier results preserved on failure.
- Parsing and retry behaviour.
- Exporters: columns, escaping, Azure `Title 1`/`Title 2`.
- Prompt files: all four exist in both languages with required sections (persona, output format, rules).
- GitHub Actions runs the suite on each push.
- Output quality is shown through author-reviewed examples, not automated tests.

## 11. Portfolio deliverables

**README (both languages), in order:** title, value line, build badge, demo GIF → the problem (only claims the author can support; otherwise PO experience) → the solution and flow diagram → product decisions (why INVEST reviewer, why Gherkin, why interview is v2) → before/after story with INVEST scores → run in 3 commands, demo mode, free providers (verify current limits) → import guides → roadmap, honest limitations, license.

**CV / LinkedIn text (delivered in chat at the end, not in the repo):** one project line and three result bullets, plus repo link and a suggestion to pin the repo.

## 12. Risks

- Azure DevOps and Jira CSV formats change by version: verify against official docs.
- Free-tier provider limits change: README tells users to check.
- Examples must be generated and reviewed by the author so they do not read as generic.

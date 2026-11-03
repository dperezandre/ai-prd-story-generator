# Prompt design notes

How the four prompts in `prompts/<lang>/` are built, and why. (Português: the same techniques apply to `prompts/pt-BR/`.)

## The pipeline at a glance

| Step | File | Persona | Input | Output |
|---|---|---|---|---|
| 1 | `01_prd.md` | Senior Product Manager | The feature idea | PRD JSON |
| 2 | `02_stories.md` | Product Owner who splits work | PRD JSON | Epics and stories |
| 3 | `03_invest_review.md` | Demanding backlog gatekeeper | PRD + stories | INVEST scores, verdicts, rewrites |
| 4 | `04_gherkin.md` | BDD practitioner | PRD + final stories | Gherkin scenarios per story |

Each step receives only what it needs. Step 2 reads the PRD, not the raw idea, so every story is traceable to a requirement (`prd_ref`).

## Techniques and why they are there

1. **A persona with a job, not a costume.** The PRD writer separates facts from guesses; the reviewer is *adversarial by design* ("fair but never generous"). Without that stance, models rate their own stories as fine.
2. **Assumptions are a first-class output.** Anything the idea does not state must go to `assumptions` or `open_questions`. The prompts forbid inventing numeric targets or baselines. This is the main defence against polished but fabricated PRDs.
3. **An objective rubric instead of "judge the quality".** INVEST is scored 0-2 per criterion, with a test for each score. Example: *Small* is 2 for 5 points or fewer, 1 for 6-8, 0 above 8.

   | Criterion | 2 | 1 | 0 |
   |---|---|---|---|
   | Independent | ships in any order | soft dependency | cannot ship without a named story |
   | Negotiable | states the need | hints at a solution | prescribes the implementation |
   | Valuable | clear user/business value | vague value | no value |
   | Estimable | team could size it now | small clarification needed | too unclear |
   | Small | 5 points or fewer | 6-8 | more than 8 |
   | Testable | clear pass/fail check | partly subjective | unverifiable ("fast", "nice") |

4. **A fixed JSON contract.** Each prompt lists the exact keys. `src/models.py` validates the reply; an invalid reply gets one retry with the validation error appended. This keeps the exporters deterministic.
5. **Few-shot with a good and a bad example.** The bad example shows the failure the rubric is meant to catch (implementation-flavoured stories, vague adjectives, URLs in Gherkin).
6. **Gherkin rules written as constraints.** One behaviour per scenario; the scenario name states the business rule; business language only (no buttons, URLs or tables); at least a success path, an alternative and an error case.
7. **Rewrite, do not split, in the review step.** Splitting would change ids and break traceability. If a story is too big, the reviewer shrinks its scope and records what was cut in `comment`.
8. **Language by folder.** `prompts/en` and `prompts/pt-BR` are written natively in each language, not machine-translated; JSON keys and enum values (`Must`, `pass`, `rewrite`) stay in English so the code is language-agnostic.

## What the automated tests check, and what they do not

`tests/test_prompts.py` guarantees that all eight files exist and contain the required sections and JSON key names. It cannot judge whether the prompts produce *good* specifications. Quality is shown through the hand-curated examples in `examples/` and should be re-checked whenever a prompt changes.

## Ideas for the next version

- A clarifying-interview step before the PRD (3-5 questions to the author).
- A second reviewer pass that compares the rewritten stories against the PRD scope.

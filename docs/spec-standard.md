# Functional specification standard

This is the structure the pipeline produces and the [`po-spec-review`](../skills/po-spec-review/SKILL.md) skill reviews against. It comes from comparing two real specifications written by a business area in a healthcare operation. Only the structure was reused: none of their content is in this repository.

The canonical version, with the full review checklist, is [docs/spec-standard.pt-BR.md](spec-standard.pt-BR.md) (Portuguese). Summary:

| # | Section | Required | Must contain |
|---|---|---|---|
| 0 | Document control | yes | Change log, contributors, confidentiality note |
| 1 | Feature identification | yes | Name, version, date |
| 2.1-2.2 | Objective, justification | yes | What the change enables and why now |
| 2.3 / 2.4 | As-is / To-be | yes | Facts about today; observable future behavior per actor |
| 2.5 | Systems and modules | yes | Each system with its module |
| 3.1 | User story | yes | One role, one value, no implementation |
| 3.2 | Business rules | yes | Numbered (`RN01`...), atomic, testable |
| 3.3 | Detailed specification | yes | Per field: type, allowed values, unit, required, empty behavior, source and read time |
| 3.4 | Acceptance criteria | yes | Gherkin: named scenarios, one behavior each, happy, alternative and error paths, linked to an `RN` |
| 3.5-3.6 | Prototype, test scenarios | optional | |
| 4 | Expected returns | yes | Type, indicator, baseline. Filled in, not template instruction text |
| 5 | Out of scope | yes | At least one explicit item |
| 6 | Assumptions and open questions | yes | Missing from both analyzed documents |
| 7 | Approvals | yes | Name, role, date |

In the pipeline, sections 2.3-2.5, 3.2 and 4 map to the PRD fields `as_is`, `to_be`, `systems`, `business_rules` and `expected_returns`, and stories point to rules through `rule_refs`.

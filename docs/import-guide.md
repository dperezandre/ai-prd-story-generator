# Importing the generated CSVs into Azure DevOps and Jira

The app exports two files: `azure_devops.csv` and `jira.csv`. Both contain one **Epic** row per epic followed by its **user stories**, with MoSCoW priority, story points and the Gherkin acceptance criteria.

> **Status of this guide.** The steps and column names were checked against the official Microsoft Learn and Atlassian documentation (links at the end). They were **not yet tested against a live Azure DevOps organization or Jira site**. Always import a first test file into a sandbox project.

## What is in each file

**`azure_devops.csv`**

| Column | Content |
|---|---|
| Work Item Type | `Epic` or `User Story` |
| Title 1 / Title 2 | Epic name goes in `Title 1`; story title goes in `Title 2`. This indentation creates the parent/child link. |
| Description | "As a ... I want ... so that ..." as HTML |
| Acceptance Criteria | Gherkin scenarios as HTML |
| Priority | MoSCoW mapped to 1-4 (Must=1, Should=2, Could=3, Won't=4) |
| Story Points | Estimate |
| Tags | `MoSCoW-Must`, `MoSCoW-Should`, `MoSCoW-Could`, `MoSCoW-Wont` |

**`jira.csv`**

| Column | Content |
|---|---|
| Issue Id | Unique number per row (epics first) |
| Issue Type | `Epic` or `Story` |
| Summary | Epic name or story title |
| Description | "As a ... I want ... so that ..." plus the Gherkin acceptance criteria |
| Priority | MoSCoW mapped to Highest/High/Medium/Low |
| Parent | For a story, the `Issue Id` of its epic |
| Labels | `moscow-must`, `moscow-should`, `moscow-could`, `moscow-wont` |

## Azure DevOps

### Before you start
- You need to be a member of **Project Administrators** or **Team Foundation Administrators** to import work items.
- The CSV uses `User Story`, which exists in the **Agile** process. In **Scrum** use `Product Backlog Item`; in **CMMI** use `Requirement`. Replace the value in the `Work Item Type` column before importing. Use a text editor, or in Excel open the file with **Data → From Text/CSV** and file origin **UTF-8**; a plain double-click can garble accents and, on some regional settings, put everything in one column.
- The `Story Points` column matches the Agile field name. In Scrum the field is `Effort`; rename the column header.
- The **Basic** process has `Epic` and `Issue` but no `Story Points` or `Acceptance Criteria` fields: use `Issue` as the work item type and delete those two columns.
- Export two or three existing work items from your project first. The exported header shows the exact field names your process uses.

### Steps
1. In the app, download **Azure DevOps CSV**.
2. In your project, open **Boards → Queries → Import work items**.
3. Select **Choose file**, pick `azure_devops.csv`, then select **Import**.
4. The items load in the query view **unsaved**, without IDs. Check the result.
5. Fix any row highlighted in red (invalid value), then select **Save items**.

### Good to know
- Text that starts with `=`, `+`, `-` or `@` is exported with a leading apostrophe so spreadsheets do not run it as a formula. The apostrophe is imported as part of the text; remove it by hand if it bothers you.
- Hierarchy comes from `Title 1` (epic) and `Title 2` (story): each story is linked as a child of the epic above it.
- Up to 1,000 work items per import.
- New items are created in state **New**, and Area/Iteration default to the project root. Add `Area Path` and `Iteration Path` columns if you need others.
- Leave the `ID` column out. Importing an ID on a new item fails.

### Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| Row in red, "invalid work item type" | The process has no `User Story` | Use your process's type (see above) |
| Unknown field error | Column name does not exist in your process | Rename the column to the exact field name from an export |
| Accents look broken | File opened and saved in a non-UTF-8 editor | Re-export from the app; keep UTF-8 |
| Acceptance Criteria shows raw `<p>` tags | The field is plain text in your process | Remove the tags, or switch the field to HTML |

## Jira Cloud

### Before you start
- Importing CSV with parent links is done by a **site or organization admin**. Non-admins need the "Create work items" and "Make bulk changes" permissions and are limited to 250 items per file.
- The target project should be **company-managed** and have the issue types `Epic` and `Story`. Imports cannot create new statuses, types or custom fields; the project must already match.
- `Epic Link` and `Epic Name` are deprecated; this file links stories to epics with `Parent`.
- If `Parent` does not appear when mapping fields, enable sub-tasks under System → Work items → Sub-Tasks.

### Steps
1. In the app, download **Jira CSV**.
2. Go to **Settings (gear) → System → External system import → CSV**. If Jira offers the new experience, you may need to switch to the old one to map fields.
3. Choose `jira.csv` and select **Next**.
4. Select the destination project. Keep the default date and email formats.
5. Map the fields: `Issue Id → Issue id`, `Issue Type → Issue Type`, `Summary → Summary`, `Description → Description`, `Priority → Priority`, `Parent → Parent`, `Labels → Labels`.
6. Select **Next**, then **Begin import**.
7. Open one story and confirm its **Parent** is the right epic.

### Good to know
- The importer processes rows top to bottom, so a parent must appear above its children. The exported file already respects this (each epic row precedes its stories).
- `Parent` holds the numeric `Issue Id`, not a key such as `PROJ-1`.
- Priorities must exist in the project (`Highest`, `High`, `Medium`, `Low` are the defaults).

### Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| Stories imported without epic | `Parent` not mapped, or parent row below the child | Map `Parent`; keep epics above stories |
| "Issue type not found" | Project has no `Epic` or `Story` type | Add the type to the project scheme |
| Priority ignored | Value not in the project's priority scheme | Rename values in the CSV or add the priority |
| Parent link fails for an epic that already exists | Known limitation when linking to existing parents | Import epics and stories in the same file |

## Official documentation
- [Azure Boards: export, update and import work items with CSV](https://learn.microsoft.com/en-us/azure/devops/boards/queries/import-work-items-from-csv)
- [Atlassian: keep parent-child relationships during CSV import to Jira Cloud](https://support.atlassian.com/jira/kb/keep-issue-parent-child-mapping-during-csv-import-to-jira-cloud/)
- [Atlassian: import work into an existing space using CSV](https://support.atlassian.com/jira-software-cloud/docs/import-issues-into-an-existing-space-in-jira-using-csv/)

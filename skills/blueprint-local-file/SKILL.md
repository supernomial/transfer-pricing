---
name: blueprint-local-file
description: Prepare OECD-compliant transfer pricing local file documentation. Use when the user asks to "prepare a local file", "create transfer pricing documentation", "draft a local file report", or "prepare documentation" for an entity.
metadata:
  author: Supernomial
  version: 0.4.0
---

# Prep Local File Skill

You assist transfer pricing professionals with OECD-compliant local file reports. You do not provide tax advice -- all output must be reviewed by qualified TP professionals.

## Working Directory

The plugin folder is **read-only**. All work goes in the user's selected folder.
- User must select a folder on the Cowork home screen BEFORE starting a task. If missing, ask them to go back and select one.
- `.library/` at root holds firm-level reusable content. Client folders use `.records/` for data and playbooks.
- NEVER write to the plugin folder or temp directories.

## Playbooks

A playbook defines the recipe for a deliverable — which sections exist, their order, and instructions for Claude.

**Folder format:** A playbook is a folder containing `playbook.md` and an optional `verbatim/` subfolder with default content files. Single `.md` files are still supported as legacy format.

**Playbook format:** Uses markdown headings for structure:
- `### Section: Title` — top-level chapter
- `#### Subsection: Title` — child section
- `##### Subsubsection: Title` — grandchild section
- `Instruction:` — guidance for Claude on how to produce that section (required at every level)

Claude derives section IDs from titles by converting to kebab-case (e.g., "Executive Summary" → `executive-summary`, "Executive Summary / Objective" → `executive-summary/objective`).

**Inheritance:** A playbook can extend another via `extends:` in frontmatter (e.g., `extends: standard-oecd-local-file`). The child defines only differences: new sections (add normally), changed instructions (redefine the heading), removed sections (`### Remove: Section Title`). Claude merges parent + child at runtime.

**Versioning:** Frontmatter `version:` (e.g., `version: "1.0"`) is stored in the view JSON as `playbook_version`. Claude warns the user if the playbook version has changed since the last generation.

**Override hierarchy** (highest wins):

| Level | Location | When to use |
|---|---|---|
| 1. Universal | `skills/blueprint-local-file/references/playbooks/` | Ships with plugin. Standard OECD structure. |
| 2. Firm | `.library/playbooks/` | Firm-wide customization. Overrides universal. |
| 3. Group | `[Group]/.records/playbooks/` | Client-specific structure. Overrides firm. |
| 4. Entity | `[Group]/.records/playbooks/[entity-id]/` | Entity-specific structure. Overrides all. |

**Selection logic:**
1. Check the entity's local file record in `data.json` for a saved `playbook` path. If present, reuse it.
2. If no saved preference, scan for playbooks at each level (folders containing `playbook.md`, or legacy `.md` files): entity → group → firm → universal.
3. Multiple playbooks can exist at the same level. If only the standard OECD playbook is found, use it. If multiple exist, ask the user to choose.
4. Save the selected playbook path on the entity's local file record in `data.json` so subsequent runs reuse it without re-asking. User can change at any time.
5. If a saved playbook path no longer exists, fall back to scanning and inform the user.

Every playbook has a `name` in its frontmatter (e.g., `name: Standard`). Claude reads this and sets `document.playbook_name` in the view JSON. The Preview displays it in the top bar.

To create or customize playbooks, use the `/playbook` command.

## Content Layers

Claude reads from multiple layers when building the view JSON. Each layer overrides the one above.

| Layer | Source | Resolves to |
|---|---|---|
| 1. Playbook default | Active playbook's `verbatim/` folder | Built-in defaults bundled with the playbook |
| 2. Firm | `.library/` in working dir | Firm-wide reusable content |
| 3. Group | `[Group]/.records/content/` | Group-specific content |
| 4. Entity | `[Group]/.records/content/[entity-id]/` | Entity-specific content |

## Content Resolution

For each section in the playbook, Claude resolves content using the section's content path. The content path is derived from the section hierarchy by converting titles to kebab-case:

- Section "Executive Summary" → content path `executive-summary/`
- Subsection "Objective" under "Executive Summary" → content path `executive-summary/objective`

**Resolution steps (highest priority wins):**

| Priority | Source | Path |
|---|---|---|
| 1 (highest) | Entity content | `[Group]/.records/content/[entity-id]/[content-path].md` |
| 2 | Group content | `[Group]/.records/content/[content-path].md` |
| 3 | Firm content | `.library/[content-path].md` |
| 4 | Playbook verbatim | Active playbook's `verbatim/[content-path].md` |
| 5 (lowest) | Generate | From playbook `Instruction:` |

**Steps:**
1. Derive the content path from the playbook section title
2. Check for a `.md` file at each priority level (highest wins)
3. Read the `.md` file at the highest-priority match
4. Use the **literal file contents** as the element's `text` field in the view JSON. Do NOT rewrite, summarize, or generate your own text — copy the file contents exactly as they are. Only substitute these placeholders: `[Entity Name]`, `[Group Name]`, `[Fiscal Year]`, `[Country]`.
5. If no content file exists at any level, use the playbook's `Instruction:` to generate content.
6. Set `meta.layer`, `meta.label`, `meta.color` based on which layer the content came from

If a section's instruction says to generate a table from data (e.g., transactions), build an `auto_table` from `transactions[]` in `data.json`. Resolve `from_entity` and `to_entity` IDs to entity names using the `entities[]` array.

## Data Model

`data.json` per group uses a minimal structure:

```json
{
  "group": { "id": "", "name": "", "country": "" },
  "entities": [
    { "id": "", "name": "", "country": "" }
  ],
  "transactions": [
    { "id": "", "description": "", "from_entity": "", "to_entity": "", "currency": "", "amount": "" }
  ],
  "local_files": [
    { "id": "", "entity_id": "", "fiscal_year": "", "status": "draft", "playbook": "" }
  ]
}
```

- `group`: the multinational group
- `entities[]`: legal entities within the group
- `transactions[]`: intercompany transactions between entities
- `local_files[]`: tracks report status and playbook selection per entity/year

**Saving user edits:** When a user edits a section for a specific entity, update the view JSON directly (it's the source of truth for that entity's report). Then regenerate outputs (preview + PDF).

Content `.md` files are for **reusable** content only:
- Firm-wide (reusable across all clients) → `.library/executive-summary/objective.md`
- Group-wide (shared across entities in this group) → `[Group]/.records/content/executive-summary/objective.md`

Entity-specific content files (`[Group]/.records/content/[entity-id]/...`) are used during initial generation. After the view JSON exists, entity edits go directly into the view JSON.

## View JSON

Claude produces a structured JSON file following `references/view-json-schema.md`. Key rules:
- Section IDs use kebab-case with `/` separators: `executive-summary/objective`
- Element keys use underscore format: `executive_summary_objective`
- Top-level sections become chapters, children become sections/subsections
- Auto sections (`is_auto: true`) use `auto_table` instead of `text`

## Memory

When working on a local file, check for relevant memory before generating or editing content:

1. **Read memory.** Before starting work, scan topic files in these folders (if they exist):
   - `.supernomial/my-memory/` — personal preferences
   - `.library/firm-memory/` — firm conventions
   - `[Group]/.records/group-memory/` — client-level context
   - `[Group]/.records/entity-memory/[entity-id]/` — entity facts
   - `[Group]/.records/file-memory/[entity-id]_FY[year]/` — report-specific notes

2. **Update memory.** After method choices, policy interpretations, client conventions, or any decision worth preserving — update the appropriate memory file with a date-stamped entry (`### YYYY-MM-DD`). Create new topic files as needed.

3. **Keep entries factual.** Decisions, facts, preferences. Not session logs or summaries.

## Folder Structure

When a new group is created, ensure this structure exists:

```
[Group Name]/
├── 1. Admin/
├── 2. Source Files/
├── 3. Working Papers/
├── 4. Deliverables/          ← PDF only (always regenerable)
└── .records/
    ├── data.json
    ├── views/                ← view JSON (source of truth) + preview HTML
    ├── content/
    │   └── [entity-id]/
    ├── playbooks/
    │   └── [entity-id]/
    ├── group-memory/         ← client-level memory (topic files)
    ├── entity-memory/
    │   └── [entity-id]/      ← entity-specific memory (topic files)
    └── file-memory/
        └── [entity-id]_FY[year]/  ← deliverable-specific memory (topic files)
```

## References

Content and schemas in `references/`:
- `view-json-schema.md` -- view JSON schema for the Preview
- `playbooks/` -- standard playbook definitions
- `style-guide.md` -- conversation tone and report writing style

## Style Guide

Read `references/style-guide.md` -- Part 1 (conversation tone) always applies. Check `.library/style-guide.md` in the user's folder for report writing style override.

## Business-Friendly Language (Mandatory)

NEVER say "JSON", "blueprint", "schema", "template", "playbook", "records folder", or other technical terms. Say "your data", "the report", "the preview". Run scripts silently, present results. Do not describe internal architecture unless the user asks.

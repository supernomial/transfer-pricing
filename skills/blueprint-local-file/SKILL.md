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

A playbook is an `.md` file defining the recipe for a deliverable — which sections exist, their order, and instructions for Claude.

**Playbook format:** Uses markdown headings for structure:
- `### Section: Title` — top-level chapter
- `#### Subsection: Title` — child section
- `##### Subsubsection: Title` — grandchild section
- `Instruction:` — guidance for Claude on how to produce that section (required at every level)

Claude derives section IDs from titles by converting to kebab-case (e.g., "Executive Summary" → `executive-summary`, "Executive Summary / Objective" → `executive-summary/objective`).

**Override hierarchy** (highest wins):

| Level | Location | When to use |
|---|---|---|
| 1. Universal | `skills/blueprint-local-file/references/playbooks/` | Ships with plugin. Standard OECD structure. |
| 2. Firm | `.library/playbooks/` | Firm-wide customization. Overrides universal. |
| 3. Group | `[Group]/.records/playbooks/` | Client-specific structure. Overrides firm. |
| 4. Entity | `[Group]/.records/playbooks/[entity-id]/` | Entity-specific structure. Overrides all. |

**Selection logic:**
1. Check the entity's local file record in `data.json` for a saved `playbook` path. If present, reuse it.
2. If no saved preference, scan for `.md` files at each level: entity → group → firm → universal.
3. Multiple playbooks can exist at the same level. If only the standard OECD playbook is found, use it. If multiple exist, ask the user to choose.
4. Save the selected playbook path on the entity's local file record in `data.json` so subsequent runs reuse it without re-asking. User can change at any time.
5. If a saved playbook path no longer exists, fall back to scanning and inform the user.

Every playbook has a `name` in its frontmatter (e.g., `name: Standard`). Claude reads this and sets `document.playbook_name` in the view JSON. The Preview displays it in the top bar.

When a user wants a custom playbook, guide them to create one with a `name` in the frontmatter (e.g., `name: Deloitte NL`) and save it at the right level:
- Custom for this entity only → entity level
- Custom for all entities in this group → group level
- Custom for all clients at the firm → firm level

## Content Layers

Claude reads from 4 layers when building the view JSON. Each layer overrides the one above.

| Layer | Prefix | Resolves to |
|---|---|---|
| 1. Universal | `@references/` | `skills/blueprint-local-file/references/` |
| 2. Firm | `@library/` | `.library/` in working dir |
| 3. Group | `@group/` | `[Group]/.records/content/` |
| 4. Entity | `@entity/` | `[Group]/.records/content/[entity-id]/` |

## Content Resolution

For each section in the playbook, Claude resolves content using the section's content path. The content path is derived from the section hierarchy by converting titles to kebab-case:

- Section "Executive Summary" → content path `executive-summary/`
- Subsection "Objective" under "Executive Summary" → content path `executive-summary/objective`

**Resolution steps:**
1. Derive the content path from the playbook section title
2. Check for a `.md` file at each layer (highest wins):
   - `[Group]/.records/content/[entity-id]/executive-summary/objective.md` → Layer 4
   - `[Group]/.records/content/executive-summary/objective.md` → Layer 3
   - `.library/executive-summary/objective.md` → Layer 2
   - `skills/blueprint-local-file/references/executive-summary/objective.md` → Layer 1 (fallback)
3. Read the `.md` file at the highest-layer match
4. Use the **literal file contents** as the element's `text` field in the view JSON. Do NOT rewrite, summarize, or generate your own text — copy the file contents exactly as they are. Only substitute these placeholders: `[Entity Name]`, `[Group Name]`, `[Fiscal Year]`, `[Country]`.
5. If no content file exists at any layer, use the playbook's `Instruction:` to generate content.
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

**Saving user content:** When a user provides custom content for a section, save it at the appropriate layer using the content path:
- Firm-wide (reusable across all clients) → `.library/executive-summary/objective.md`
- Group-wide (shared across entities in this group) → `[Group]/.records/content/executive-summary/objective.md`
- Entity-specific → `[Group]/.records/content/[entity-id]/executive-summary/objective.md`

The content auto-resolves on next generation — no playbook change needed.

## View JSON

Claude produces a structured JSON file following `references/view-json-schema.md`. Key rules:
- Section IDs use kebab-case with `/` separators: `executive-summary/objective`
- Element keys use underscore format: `executive_summary_objective`
- Top-level sections become chapters, children become sections/subsections
- Auto sections (`is_auto: true`) use `auto_table` instead of `text`

## Folder Structure

When a new group is created, ensure this structure exists:

```
[Group Name]/
├── 1. Admin/
├── 2. Source Files/
├── 3. Working Papers/
├── 4. Deliverables/
└── .records/
    ├── data.json
    ├── session-log.json
    ├── views/
    ├── content/
    │   └── [entity-id]/
    └── playbooks/
        └── [entity-id]/
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

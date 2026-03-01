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

A playbook is an `.md` file defining the recipe for a deliverable — which sections, what order, which content sources.

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

Every playbook has a `name` in its frontmatter (e.g., `name: Standard`). Claude reads this and sets `document.playbook_name` in the view JSON. The Workspace Editor displays it in the top bar.

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

For each section in the playbook, Claude resolves the actual text as follows:

1. Read the content source from the playbook (e.g., `@references/preamble/objective`)
2. Extract the relative path: `preamble/objective`
3. Check for overrides at higher layers using the same relative path (highest wins):
   - `[Group]/.records/content/[entity-id]/preamble/objective.md` → Layer 4
   - `[Group]/.records/content/preamble/objective.md` → Layer 3
   - `.library/preamble/objective.md` → Layer 2
   - `skills/blueprint-local-file/references/preamble/objective.md` → Layer 1 (fallback)
4. Read the `.md` file at the highest-layer match
5. Use the file contents as the element's `text` field in the view JSON
6. Set `meta.layer`, `meta.label`, `meta.color` based on which layer the content came from

**Note:** Content paths in the playbook may differ from section IDs. Override files must use the same relative path as the content source (e.g., `preamble/objective`), not the section ID hierarchy (e.g., `executive-summary/objective`).

If the content source is `(auto)`, build an `auto_table` from structured data in `data.json` instead. For auto tables that display entity names (e.g., transactions overview), resolve `from_entity` and `to_entity` IDs to names using the `entities[]` array in `data.json`.

**Saving user content:** When a user provides custom content for a section, save it at the appropriate layer:
- Firm-wide (reusable across all clients) → `.library/preamble/objective.md`
- Group-wide (shared across entities in this group) → `[Group]/.records/content/preamble/objective.md`
- Entity-specific → `[Group]/.records/content/[entity-id]/preamble/objective.md`

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
- `view-json-schema.md` -- view JSON schema for the Workspace Editor
- `playbooks/` -- standard playbook definitions
- `style-guide.md` -- conversation tone and report writing style
- `preamble/` -- Executive Summary section content

## Style Guide

Read `references/style-guide.md` -- Part 1 (conversation tone) always applies. Check `.library/style-guide.md` in the user's folder for report writing style override.

## Business-Friendly Language (Mandatory)

NEVER say "JSON", "blueprint", "schema", "template", "playbook", "records folder", or other technical terms. Say "your data", "the report", "the preview". Run scripts silently, present results. Do not describe internal architecture unless the user asks.

---
description: Manage report structures and content defaults — view, create, or customize playbooks
argument-hint: "<view, create, content, or compare>"
---

# /playbook — Manage Playbooks & Content

Manage report structures (playbooks) and content defaults. Use this command to view available playbooks, create custom ones, set up reusable content, or compare structures.

## Invocation

```
/playbook <action>
```

Action: @$1

## Step 1: Validate Subscription

```bash
python3 auth/gateway.py validate --working-dir .
```

Exit 0 = proceed. Exit 1 = show the error from stderr in business-friendly language. Never expose script names, flags, or error codes.

## Step 2: Determine Action

Based on user input, determine the action. If unclear, ask:

1. **View** — "What report structures are available?"
2. **Create** — "I want a custom report structure"
3. **Content** — "I want to set default content for a section"
4. **Compare** — "How does my custom structure differ from standard?"

## Step 3: Execute Action

### View

Scan all 4 levels for playbooks (folders containing `playbook.md`, or legacy single `.md` files):

| Level | Location |
|---|---|
| Universal | `skills/blueprint-local-file/references/playbooks/` |
| Firm | `.library/playbooks/` |
| Group | `[Group]/.records/playbooks/` |
| Entity | `[Group]/.records/playbooks/[entity-id]/` |

Present a clear summary:
- Which playbooks exist at each level
- Which entities use which playbook (from `data.json` local file records)
- Highlight any saved preferences that point to missing playbooks

### Create

Ask the user:
1. **Scope:** Firm-wide, for a specific client group, or for a specific entity?
2. **Starting point:**
   - **(a) Start from the standard structure and customize** — Creates a playbook with `extends: standard-oecd-local-file` in frontmatter. Ask the user what they want to change conversationally (add sections, remove sections, change instructions). Write only the differences.
   - **(b) Build from scratch** — Walk through section by section. Ask what chapters they need, what subsections, any special instructions.

**Inheritance syntax** (for option a):
```markdown
---
name: Firm Custom
version: "1.0"
extends: standard-oecd-local-file
---

# Changes from Standard OECD Local File

### Section: Regulatory Analysis

Instruction: Prepare local regulatory overview covering country-specific TP rules and documentation requirements.

### Remove: Industry Analysis
```

- New sections: add normally with `### Section:` headings
- Changed instructions: redefine the heading with new instruction
- Removed sections: `### Remove: Section Title`

Save the playbook at the correct level:
- Firm → `.library/playbooks/[name]/playbook.md`
- Group → `[Group]/.records/playbooks/[name]/playbook.md`
- Entity → `[Group]/.records/playbooks/[entity-id]/[name]/playbook.md`

Never ask the user to edit files manually. Claude writes everything based on the conversation.

### Content

Help the user set reusable content at the right level:

1. Ask which section (e.g., "Business Description", "Executive Summary / Objective")
2. Ask the scope: firm-wide, group-wide, or entity-specific
3. Accept the content (pasted text, dictated, or from a file)
4. Save as a `.md` file at the correct location:
   - Firm → `.library/[content-path].md`
   - Group → `[Group]/.records/content/[content-path].md`
   - Entity → `[Group]/.records/content/[entity-id]/[content-path].md`
5. Explain which reports this affects: "This will be used for all [scope] reports that include this section, unless overridden at a more specific level."

### Compare

Compare two playbooks structurally:
1. Ask which playbooks to compare (or default to firm vs. standard)
2. For extending playbooks, resolve the full structure by merging parent + child
3. Show differences: added sections, removed sections, changed instructions
4. Present in a clear, non-technical format

## Language Rules

- NEVER expose implementation details: no JSON, script names, file paths, flags, schema terms.
- Say "report structure" not "playbook". Say "default content" not "verbatim". Say "section" not "element".
- Say "your firm's version", "the standard structure", "client-specific version".
- After creating or modifying any file, confirm what was done in plain language.

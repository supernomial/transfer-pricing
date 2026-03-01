---
description: Prepare a complete OECD-compliant transfer pricing local file — from intake to final deliverable
argument-hint: "<entity name, data file, or text>"
---

# /prep-local-file -- Prepare a Local File Against a Blueprint

Prepare a transfer pricing local file against a blueprint. Clearly understand user intent and align preparation against these goals. Prepare report section by section, review, confirm results with user, and suggest next steps.

## Invocation

```
/prep-local-file <file, text, country, or entity>
```

Prepare the local file: @$1


## Workflow



### Step 1: Validate Subscription

```bash
python3 auth/gateway.py validate --working-dir .
```

Exit 0 = proceed. Exit 1 = show the error from stderr in business-friendly language. Never expose script names, flags, or error codes.



### Step 2: Clarify User's General Intent

Ask the user for what they plan to achieve:

1. **Prepare from scratch or continue from existing file**
2. **Review and improve a file**
3. **Plan a new file**
3. **Learn and see examples**
4. **Other**

If working folder is not selected, ask the user to go back to the Cowork home screen, click "Work in a folder", and start a new task.



### Step 3: Accept any Provided Information (if any)

Accept any information provided by user:

- **File upload**: PDF, DOCX, or other document format
- **URL**: Link to local file, cloud storage (e.g., Google Drive or SharePoint), or other document system
- **Pasted text**: Local File text pasted directly into the conversation
- **Indicated location**: Working directory folder or file name provided by user



### Step 4: Gather Context

Gather or confirm context before assisting user.

1. **Does group or entity folder and file already exist?**: Silently check and/or infer from previous steps.
2. **Check project status, notes, and memory files**
3. **Confirm understanding with user**: Indicate your understanding of groups, entities, files to work on or create from scratch.
3. **Focus areas**: If applicable, ask for any specific areas of the Local File to focus on.
4. **Ask for further context user would like to provide**



### Step 5: Silently Load Memory and Style Guides

Load memory and any project update files as well as style guides to enrich conversation going forward.

1. **Load memory.** Follow `skills/memory/SKILL.md` -- read personal, group, and firm memory silently.
2. **Load style guide.** Read `skills/local-file/references/style-guide.md` -- apply Part 1 (conversation tone) always. Check `.library/style-guide.md` for report writing style override.



## Step 6: Prepare and Generate Workspace Editor

Use playbook and blueprint to assemble the **view JSON** which then renders the Workspace Editor

Definitions:

**Blueprint**: A local file Blueprint is a skill in plugin files that section by section prepares a structured **view JSON** in a predetermined format so that the **Workspace Editor** and **Final PDF** render it consistently. What is flexible is the section/subsection names, section/subsection order, types of content blocks (universal, firm, group, or entity level) within each section/subsection and order, and the content of each content block. The Blueprint is prepared based on instructions in the Playbook and the information contained in Group JSON data file, the skill file for each section (e.g. Executive Summary skill) and content blocks available as .md files from universal, firm, group, and entity level.

**Playbook**: A local file Playbook is an .md file that exists as part of the plugin (standard OECD local file playbook) that lists in a table section type (e.g. Executive Summary), section header (e.g. Executive Summary), section content blocks to be pulled from the four levels (universal, firm, group, entity).

### 6a. Load the Playbook

1. Check `.library/playbooks/` in the working directory for a firm override playbook. If found, use it.
2. If no firm override, use the standard playbook: `skills/local-file/references/playbooks/oecd-local-file.md`.
3. Parse the markdown table — each row defines a section with ID, title, parent, and content sources.

### 6b. Walk Sections and Resolve Content

For each section row in the playbook (in order):

1. **Read content sources.** For each source in the Content Sources column:
   - `@references/...` → read from `skills/local-file/references/` (Layer 1)
   - `@library/...` → read from `.library/` in working directory (Layer 2)
   - `@group/...` → read from `[Group]/.records/content/` (Layer 3)
   - `@entity/...` → read from `[Group]/.records/content/[entity-id]/` (Layer 4)
   - `(auto: ...)` → build auto_table from structured data in `data.json`
2. **Substitute placeholders.** Replace `[Entity Name]`, `[Group Name]`, `[Fiscal Year]`, `[Country]` with values from the entity/group data.
3. **Determine layer metadata.** Set `meta.layer`, `meta.label`, `meta.color`, `meta.scope` based on the highest-layer content source used.
4. **If multiple sources exist for one section**, mark `composite: true` and build a `parts` array.

### 6c. Build View JSON

1. **Map playbook hierarchy to chapters array.** Top-level sections (parent = `—`) become chapters. Sections with a parent become `sections` within that chapter. Nested children become `subsections`.
2. **Create element keys.** Convert section IDs from kebab-case with `/` to underscore format: `executive-summary/objective` → `executive_summary_objective`.
3. **Populate the elements object.** Each key maps to the resolved content, metadata, notes, footnotes, and status per `view-json-schema.md`.
4. **Fill document, progress, general_notes, blueprints, jurisdiction_svg** from `data.json` and blueprint data.

### 6d. Write Output and Generate Workspace Editor

1. Write the view JSON to `[Group]/.records/views/[entity-id]_workspace_FY[year].json`.
2. Run `generate_workspace.py` to produce the HTML:
   ```bash
   python3 skills/local-file/scripts/generate_workspace.py \
     --view-json "[Group]/.records/views/[entity-id]_workspace_FY[year].json" \
     --template skills/local-file/assets/combined_view.html \
     --brand assets/brand.css \
     --output "[Group]/4. Deliverables/FY[Year]/Local File/[Country]/[Entity]/[Entity]_Workspace_Editor_FY[Year].html"
   ```
3. Present the generated file to the user. Do NOT read the file back — just confirm it was created.



## Step 7: Prepare Final PDF

[...]



## Step 8: Review

[...]



## Step 9: Wrap Up

1. **Session log.** Append to `[Group]/.records/session-log.json` (date, command, entity, summary, decisions, pending). Log continuously -- users close chats randomly.
2. **Consolidate memory.** Follow `skills/memory/SKILL.md` consolidation rules.
3. **Present next steps.** Show where the deliverable is saved, suggest what to do next.



## Language Rules

- NEVER expose implementation details to the user: no JSON, script names, file paths, flags, schema terms, "blueprint", "records folder".
- Say "your data", "the report", "the preview" -- not "data.json", "the view JSON", etc.
- After generating any file, present it to the user. Do NOT read generated files back.

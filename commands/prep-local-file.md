---
description: Prepare a complete OECD-compliant transfer pricing local file — from intake to final deliverable
argument-hint: "<entity name, data file, or text>"
---

# /prep-local-file -- Prepare a Local File

Prepare a transfer pricing local file. Understand user intent, prepare report section by section, confirm results, and suggest next steps.

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
2. **Check project status**
3. **Confirm understanding with user**: Indicate your understanding of groups, entities, files to work on or create from scratch.
3. **Focus areas**: If applicable, ask for any specific areas of the Local File to focus on.
4. **Ask for further context user would like to provide**

**Create memory folders** when initializing a new group or entity:

- New group → create `[Group]/.records/group-memory/` alongside the other `.records/` subfolders
- New entity deliverable (first view JSON for an entity) → create:
  - `[Group]/.records/entity-memory/[entity-id]/`
  - `[Group]/.records/file-memory/[entity-id]_FY[year]/`



### Step 5: Load Style Guide

1. **Load style guide.** Read `skills/blueprint-local-file/references/style-guide.md` -- apply Part 1 (conversation tone) always. Check `.library/style-guide.md` for report writing style override.



## Step 6: Prepare the Local File

Read `skills/blueprint-local-file/SKILL.md` for reference context. Then:

1. **Consider context** gathered in Steps 1–5.
2. **Select playbook.** Check if the entity's local file record in `data.json` has a saved `playbook` preference. If yes and the file exists, reuse it silently. If the saved path doesn't exist, fall back to scanning and inform the user. If no preference saved:
   - Scan for playbooks at each level (folders containing `playbook.md`, or legacy single `.md` files): entity (`[Group]/.records/playbooks/[entity-id]/`) → group (`[Group]/.records/playbooks/`) → firm (`.library/playbooks/`) → universal (`skills/blueprint-local-file/references/playbooks/`)
   - If only the standard OECD playbook exists, use it and confirm briefly.
   - If multiple playbooks exist at any level, list them and let the user choose.
   - If the user wants a custom report structure, suggest: "You can set up a custom report structure with `/playbook`."
   - Save the selected playbook path on the entity's local file record in `data.json` as `playbook` so it's reused next time.
   - For extending playbooks (`extends:` in frontmatter), resolve the full structure by merging parent + child before proceeding.
3. **Populate view JSON** based on playbook instructions. Read the playbook's frontmatter `name` and set `document.playbook_name` in the view JSON (standard playbook = "Standard"). Read `version` from frontmatter and set `document.playbook_version` in the view JSON. If the entity already has a view JSON with a different `playbook_version`, warn the user that the report structure has been updated since the last generation before proceeding. For each section in the playbook:
   - Derive the content path from the section title (kebab-case, e.g., "Executive Summary / Objective" → `executive-summary/objective`)
   - Check for `.md` content files at each level (entity → group → firm → playbook verbatim). If found, **use `cat` to read the file** and paste the exact contents as the element's `text` field. Do NOT paraphrase, summarize, or generate your own version.
   - If no content file exists at any level (including playbook verbatim), generate content from the playbook's instruction for that section.
   - Only substitute these placeholders: `[Entity Name]`, `[Group Name]`, `[Fiscal Year]`, `[Country]`
   - For sections that require a data table (e.g., Transactions Under Analysis), build `auto_table` from data.json instead
   - Follow `skills/blueprint-local-file/references/view-json-schema.md`
   - **Verify content fidelity.** After populating the view JSON, spot-check at least 3 text elements against their source `.md` files. If any element text doesn't match the file contents verbatim (after placeholder substitution), fix it before proceeding.
4. **Generate Preview.** This step is mandatory — always run this script. Output goes next to the view JSON in `.records/views/`.
   ```bash
   python3 skills/blueprint-local-file/scripts/generate_preview.py \
     --view-json "[Group]/.records/views/[entity-id]_FY[year].json" \
     --template skills/blueprint-local-file/assets/preview.html \
     --brand assets/brand.css \
     --output "[Group]/.records/views/[entity-id]_FY[year].html"
   ```
5. **Generate PDF.** This step is mandatory — always run this script immediately after the Preview. Output goes in the deliverables folder (human-readable filename). Create the folder if it doesn't exist. Only the PDF should remain in the deliverables folder — the script builds in a temporary directory and copies only the PDF to the output path. Never manually place or leave .tex, .aux, .log, .out, .toc, or .html files in deliverables.
   ```bash
   python3 skills/blueprint-local-file/scripts/generate_pdf.py \
     --view-json "[Group]/.records/views/[entity-id]_FY[year].json" \
     --template skills/blueprint-local-file/assets/local_file.tex \
     --output "[Group]/4. Deliverables/FY[Year]/Local File/[Country]/[Entity Name]/[Entity Name] Local File FY[Year].pdf"
   ```
7. **Review.** Check that output aligns with user intent and playbook. Correct if needed.
8. **Present to user.** Show the Preview and PDF. Do NOT read generated files back.



## Step 7: Wrap Up

1. **Present next steps.** Show where the deliverable is saved, suggest what to do next. NEVER suggest "run /prep-local-file again" — the user can keep chatting in this conversation to edit any section, add content, or make changes. Cowork is a conversation, not a one-shot command.



## Language Rules

- NEVER expose implementation details to the user: no JSON, script names, file paths, flags, schema terms, "blueprint", "records folder".
- Say "your data", "the report", "the preview" -- not "data.json", "the view JSON", etc.
- After generating any file, present it to the user. Do NOT read generated files back.

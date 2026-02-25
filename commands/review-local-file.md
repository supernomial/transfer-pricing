---
description: Review an existing transfer pricing local file against OECD guidelines and best practices — analyze completeness, flag issues, suggest improvements
argument-hint: "<upload local file or paste text>"
---

# /review-local-file -- Review Transfer Pricing Documentation

## Step 0: Validate subscription

Before doing anything else, run:

```bash
python3 auth/gateway.py validate
```

- Exit code 0 → proceed normally.
- Exit code 1 → stop immediately and show the user the error printed to stderr. Do not proceed with any other steps.

Review an existing transfer pricing local file (PDF, Word, or text) against OECD guidelines and best practices. Analyze for completeness, identify gaps, and suggest improvements without modifying your existing records.

## Invocation

```
/review-local-file
```

## Workflow

### Step 1: Accept the Local File

Accept the local file in any of these formats:
- **File upload**: PDF, DOCX, or other document format
- **URL**: Link to a document in cloud storage
- **Pasted text**: Document text pasted directly into the conversation

If no file is provided, prompt the user to supply one.

### Step 1b: Load Context

Before beginning the review, silently load available context:

**Memory:**
1. Read `.supernomial/me.json` if it exists — adapt tone and detail level to the user's preferences
2. If the entity's group folder is known, read `[Group]/.records/memory.json` — use client context (audit status, deadlines, preferences) to inform the review focus
3. Read `.library/memory.json` if it exists — apply firm methodology and conventions to the review criteria

**Style guide:**
4. Read `skills/local-file/references/style-guide.md` — apply conversation tone (Part 1)
5. Check `.library/style-guide.md` — if found, use for report writing style (overrides Part 2)

Use memory to skip questions in Step 2 that are already known (e.g., if memory has the entity and fiscal year, don't re-ask).

### Step 2: Gather Context

Ask the user for context before beginning the review:

1. **Which entity is this for?** (helps assess relevant regulations)
2. **Fiscal year?** (ensures current OECD guidelines apply)
3. **Specific concerns?** (e.g., "ensure functional analysis is complete", "verify comparables documentation", "check if method justification is strong")
4. **Review purpose?** (internal review, tax authority filing, pre-audit preparation)

If the user provides partial context, proceed with what you have and note assumptions.

### Step 3: Analyze Against OECD Guidelines

Systematically review the local file covering:

| Section | Key Review Points |
|---------|-------------------|
| **Executive Summary** | Clear statement of conclusions, key findings summarized |
| **Entity Overview** | Legal structure, ownership, business activities, functional profile |
| **Functional Analysis** | Functions performed, assets used, risks assumed (FAR analysis) |
| **Intercompany Transactions** | All controlled transactions identified and described |
| **Transfer Pricing Method** | Appropriate method selected and justified (CUP, RPM, CPM, TNMM, PSM) |
| **Comparability Analysis** | Comparable companies/transactions identified, adjustments documented |
| **Economic Analysis** | Financial data, benchmarking, arm's length range determination |
| **Documentation** | Supporting evidence, agreements, financial statements attached |

For each section, assess whether it is present, complete, or needs improvement.

### Step 4: Flag Issues

Classify findings using a three-tier system:

#### GREEN -- Compliant
- Meets or exceeds OECD guidelines
- Well-documented and defensible
- No action needed

#### YELLOW -- Needs Improvement
- Present but could be strengthened
- Minor gaps or inconsistencies
- Recommended enhancements provided

#### RED -- Critical Gap
- Required section missing or inadequate
- Methodology concerns or insufficient support
- Likely to raise questions in audit
- Must address before filing

### Step 5: Generate Review Summary

Provide a structured output:

```
## Local File Review Summary

**Entity**: [entity name]
**Fiscal Year**: [year]
**Review Date**: [date]
**Review Basis**: OECD Guidelines / [Country-specific regulations]

## Key Findings

[Top 3-5 issues with severity flags]

## Section-by-Section Analysis

### [Section Name] -- [GREEN/YELLOW/RED]
**Status**: [description of what's present]
**OECD requirement**: [what guidelines require]
**Gap/Issue**: [description of gap, if any]
**Recommendation**: [specific improvement suggestion]

[Repeat for each major section]

## Comparability with Best Practices

[How this compares to well-prepared local files]

## Audit Risk Assessment

**Overall Risk Level**: [Low/Medium/High]
**Likely Auditor Questions**: [anticipated areas of inquiry]

## Next Steps

[Specific actions to take]
```

## Notes

- This command is for **review only** — it does not add data to your records
- Use `/prep-local-file` when you want to build documentation from your records
- Reviews can be saved as reference materials in your firm library
- All analysis should be reviewed by qualified transfer pricing professionals before being relied upon

# View JSON Schema

Reference for producing view JSON consumed by the Preview (`preview.html`).

## Top-Level Structure

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "document": { ... },
  "progress": { ... },
  "chapters": [ ... ],
  "elements": { ... },
  "general_notes": [ ... ],
}
```

## document

```json
{
  "title": "Local File",
  "subtitle": "Entity Name B.V.",
  "meta": "Transfer Pricing Documentation · FY 2024",
  "entity_id": "entity-slug",
  "entity_name": "Full Entity Name",
  "group_name": "Group Name",
  "fiscal_year": "2024",
  "country": "NL",
  "blueprint_name": "OECD Blueprint",
  "playbook_name": "Standard",
  "playbook_version": "1.0"
}
```

- Defaults: title = "Local File", subtitle = entity name, meta = "Transfer Pricing Documentation · FY {year}".
- `playbook_name`: read from the playbook's frontmatter `name` field. "Standard" for the built-in OECD playbook, custom name for user playbooks. Displayed in the Preview top bar.
- `playbook_version`: read from the playbook's frontmatter `version` field. Used to detect when a playbook has been updated since last generation.

## progress

```json
{
  "stage": "draft",
  "total_sections": 25
}
```

- `stage`: one of `"draft"`, `"review"`, `"final"`. From `local_files[].status`.

## chapters

Array describing the document outline. Three levels: chapter, section, subsection. The array must contain one chapter per `### Section` in the playbook.

```json
[
  {
    "id": "executive-summary",
    "title": "Executive Summary",
    "keys": ["executive_summary"],
    "sections": [
      {
        "id": "objective",
        "title": "Objective",
        "keys": ["executive_summary_objective"]
      },
      {
        "id": "scope",
        "title": "Scope",
        "keys": ["executive_summary_scope"]
      }
    ]
  },
  {
    "id": "business-description",
    "title": "Business Description",
    "keys": ["business_description"],
    "sections": [
      {
        "id": "group-overview",
        "title": "Group Overview",
        "keys": ["business_description_group_overview"],
        "subsections": [
          {
            "id": "organisational-structure",
            "title": "Organisational Structure",
            "keys": ["business_description_group_overview_organisational_structure"]
          }
        ]
      }
    ]
  },
  {
    "id": "industry-analysis",
    "title": "Industry Analysis",
    "keys": ["industry_analysis"],
    "sections": [
      {
        "id": "industry-overview",
        "title": "Industry Overview",
        "keys": ["industry_analysis_industry_overview"]
      }
    ]
  },
  {
    "id": "economic-analysis",
    "title": "Economic Analysis",
    "keys": ["economic_analysis"],
    "sections": [
      {
        "id": "functional-analysis",
        "title": "Functional Analysis",
        "keys": ["economic_analysis_functional_analysis"]
      }
    ]
  },
  {
    "id": "appendices",
    "title": "Appendices",
    "keys": ["appendices"]
  }
]
```

- `id` values use **kebab-case** matching the playbook section hierarchy.
- `keys` arrays hold **underscore-format** element keys that reference entries in the `elements` object.
- The renderer uses `chapter.keys`, `section.keys`, `subsection.keys` to look up elements.

### Key naming convention

Playbook section IDs use `/` separators with kebab-case: `executive-summary/objective`.
Element keys replace both `-` and `/` with `_`: `executive_summary_objective`.

## elements

Flat object keyed by underscore-format section keys. Every section, subsection, and subsubsection in the playbook must have a corresponding element entry.

```json
{
  "executive_summary": {
    "text": "Content for the Executive Summary...",
    "meta": { "layer": 1, "label": "Default", "generated": true, "source_path": "executive-summary", "scope": "universal", "color": "#64748b", "impact": "Applies to all local files" },
    "is_auto": false, "editable": false, "composite": false
  },
  "executive_summary_objective": {
    "text": "The objective of this local file is to demonstrate...",
    "meta": { "layer": 1, "label": "Default", "generated": false, "source_path": "executive-summary/objective", "scope": "universal", "color": "#64748b", "impact": "Applies to all local files" },
    "is_auto": false, "editable": false, "composite": false
  },
  "business_description": {
    "text": "Content for Business Description...",
    "meta": { "layer": 1, "label": "Default", "generated": true, "source_path": "business-description", "scope": "universal", "color": "#64748b", "impact": "Applies to all local files" },
    "is_auto": false, "editable": false, "composite": false
  },
  "industry_analysis": {
    "text": "Content for Industry Analysis...",
    "meta": { "layer": 1, "label": "Default", "generated": true, "source_path": "industry-analysis", "scope": "universal", "color": "#64748b", "impact": "Applies to all local files" },
    "is_auto": false, "editable": false, "composite": false
  }
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `text` | string | Rendered content. Empty string for auto sections. |
| `meta.layer` | int (1-4) | Content layer number. |
| `meta.label` | string | Origin label for X-ray display. Layer 1: `"Default"` (standard OECD playbook) or `"Custom"` (any custom playbook). Layers 2–4: `"Firm"`, `"Group"`, `"Entity"`. |
| `meta.generated` | bool | `true` if Claude generated this content from a playbook instruction. `false` if content was read from a saved `.md` file (verbatim, firm, group, or entity content file). |
| `meta.source_path` | string | Content path derived from section title (e.g. `executive-summary/objective`). |
| `meta.scope` | string | `"universal"`, `"firm"`, `"group"`, or `"entity"`. |
| `meta.color` | string | **Deprecated — ignored by preview.** Colors are now derived from `meta.label`. Can be omitted. |
| `meta.impact` | string | Human-readable description of content scope. |
| `notes` | string[] | Editorial notes for this section. |
| `footnotes` | string[] | Citations or footnotes for this section. |
| `is_auto` | bool | True for auto-generated table sections. |
| `editable` | bool | True when `layer >= 4` and not auto. User can edit. |
| `composite` | bool | True when section is assembled from multiple layer parts. |

### Layer colors

| Layer | Label | Color | Scope |
|---|---|---|---|
| 1 | Default | `#64748b` | `universal` |
| 1 | Custom | `#0a6afc` | `universal` |
| 2 | Firm | `#d97706` | `firm` |
| 3 | Group | `#9333ea` | `group` |
| 4 | Entity | `#059669` | `entity` |

**Label rules:** Layer 1 sections use `"Default"` when the active playbook is the standard OECD playbook (`playbook_name` = "Standard OECD Local File"), or `"Custom"` when any other playbook is active. Layers 2–4 always use their fixed labels regardless of playbook.

### Composite sections

When `composite: true`, the element includes a `parts` array. Each part has its own layer info:

```json
{
  "composite": true,
  "parts": [
    {
      "text": "Standard guidance text...",
      "layer": 1,
      "label": "Default",
      "generated": false,
      "color": "#64748b",
      "editable": false
    },
    {
      "text": "Entity-specific addition...",
      "layer": 4,
      "label": "Entity",
      "generated": true,
      "color": "#059669",
      "editable": true
    }
  ]
}
```

### Auto table sections

When `is_auto: true`, the element includes an `auto_table` object instead of `text`.

#### Transactions overview (`executive_summary_transactions_under_analysis`)

```json
{
  "auto_table": {
    "type": "transactions_overview",
    "columns": ["Description", "From", "To", "Currency", "Amount"],
    "rows": [["Licensing Fee", "Parent Corp", "Entity B.V.", "EUR", "1,250,000"]]
  }
}
```

Source: `transactions[]` in data.json. Resolve `from_entity` and `to_entity` IDs to entity names using the `entities[]` array.

## general_notes

Optional array of note groups. Currently not rendered by the Preview but reserved for future use.

```json
[
  {
    "scope": "group",
    "title": "Acme Group",
    "items": ["Key deadline: March 2025"]
  }
]
```


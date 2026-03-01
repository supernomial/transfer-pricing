# View JSON Schema

Reference for producing view JSON consumed by the Workspace Editor (`combined_view.html`).

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
  "jurisdiction_svg": "<svg>...</svg>"
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
  "playbook_name": "Standard"
}
```

- `title` / `subtitle` / `meta` can be overridden in the `local_files[]` object in data.json. Defaults: title = "Local File", subtitle = entity name, meta = "Transfer Pricing Documentation · FY {year}".
- `playbook_name`: read from the playbook's frontmatter `name` field. "Standard" for the built-in OECD playbook, custom name for user playbooks. Displayed in the Workspace Editor top bar.

## progress

```json
{
  "stage": "draft",
  "total_sections": 25,
  "reviewed_count": 10,
  "signoff_count": 5,
  "review_pct": 40,
  "signoff_pct": 20
}
```

- `stage`: one of `"draft"`, `"review"`, `"final"`. From `local_files[].status`.
- Counts derive from `local_files[].section_status`. Each key maps to `{ "reviewed": bool, "signed_off": bool }`.
- Percentages: `round(count / total_sections * 100)`.

## chapters

Array describing the document outline. Three levels: chapter, section, subsection.

```json
[
  {
    "id": "executive-summary",
    "title": "Executive Summary",
    "keys": ["executive_summary_objective"],
    "sections": [
      {
        "id": "scope",
        "title": "Scope of the Local File",
        "keys": ["executive_summary_scope"],
        "subsections": [
          {
            "id": "covered-entities",
            "title": "Covered Entities",
            "keys": ["executive_summary_scope_covered_entities"]
          }
        ]
      }
    ]
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

Flat object keyed by underscore-format section keys. Each element:

```json
{
  "executive_summary_objective": {
    "text": "Rendered markdown/text content...",
    "meta": {
      "layer": 1,
      "label": "Standard",
      "source_path": "@references/preamble/objective",
      "scope": "universal",
      "color": "#64748b",
      "impact": "Applies to all local files"
    },
    "notes": ["Editorial note string"],
    "footnotes": ["Citation or footnote string"],
    "status": {
      "reviewed": false,
      "signed_off": false
    },
    "is_auto": false,
    "editable": false,
    "composite": false
  }
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `text` | string | Rendered content. Empty string for auto sections. |
| `meta.layer` | int (1-4) | Content layer number. |
| `meta.label` | string | Layer label: `"Standard"` (1), `"Firm"` (2), `"Group"` (3), `"Entity"` (4). |
| `meta.source_path` | string | Content reference path (e.g. `@references/preamble/objective`). |
| `meta.scope` | string | `"universal"`, `"firm"`, `"group"`, or `"entity"`. |
| `meta.color` | string | Hex color for X-ray display. |
| `meta.impact` | string | Human-readable description of content scope. |
| `notes` | string[] | Editorial notes for this section. |
| `footnotes` | string[] | Citations or footnotes for this section. |
| `status.reviewed` | bool | Whether the section has been reviewed. |
| `status.signed_off` | bool | Whether the section has been signed off. |
| `is_auto` | bool | True for auto-generated table sections. |
| `editable` | bool | True when `layer >= 4` and not auto. User can edit. |
| `composite` | bool | True when section is assembled from multiple layer parts. |

### Layer colors

| Layer | Label | Color | Scope |
|---|---|---|---|
| 1 | Standard | `#64748b` | `universal` |
| 2 | Firm | `#94a3b8` | `firm` |
| 3 | Group | `#a855f7` | `group` |
| 4 | Entity | `#3b82f6` | `entity` |

### Composite sections

When `composite: true`, the element includes a `parts` array. Each part has its own layer info:

```json
{
  "composite": true,
  "parts": [
    {
      "text": "Standard guidance text...",
      "layer": 1,
      "label": "Standard",
      "color": "#64748b",
      "editable": false
    },
    {
      "text": "Entity-specific addition...",
      "layer": 4,
      "label": "Entity",
      "color": "#3b82f6",
      "editable": true
    }
  ]
}
```

### Auto table sections

When `is_auto: true`, the element includes an `auto_table` object instead of `text`. Six auto section types:

#### 1. Transactions overview (`executive_summary_transactions_under_analysis`)

```json
{
  "auto_table": {
    "type": "transactions_overview",
    "columns": ["Description", "From", "To", "Currency", "Amount"],
    "rows": [["Licensing Fee", "Parent Corp", "Entity B.V.", "EUR", "1,250,000"]]
  }
}
```

Source: `local_files[].covered_transactions` mapped to `transactions[]` in data.json. Resolve `from_entity` and `to_entity` IDs to entity names using the `entities[]` array.

#### 2. Transactions not covered (`transactions_not_covered`)

```json
{
  "auto_table": {
    "type": "transactions_not_covered",
    "columns": ["Transaction", "Counterparty", "Type", "Amount"],
    "rows": [["Admin Services", "Shared Services Ltd", "Service Fee", "500,000"]]
  }
}
```

Source: all transactions involving the entity minus those in `covered_transactions`.

#### 3. Transaction contractual terms (`tx_{N}_contractual_terms`)

Key pattern: `tx_1_contractual_terms`, `tx_2_contractual_terms`, etc.

Standard transactions: `columns: ["Term", "Detail"]`, rows are key-value pairs.
Financial transactions: transposed layout where columns are term names, single row of values.

Source: `transactions[].contractual_terms` object.

#### 4. Transaction characteristics (`tx_{N}_characteristics`)

```json
{
  "auto_table": {
    "type": "characteristics",
    "columns": ["Characteristic", "Description"],
    "rows": [["Product Type", "Licensed IP"]]
  }
}
```

Omitted for financial transaction types. Source: `transactions[].characteristics`.

#### 5. Transaction economic circumstances (`tx_{N}_economic_circumstances`)

```json
{
  "auto_table": {
    "type": "economic_circumstances",
    "columns": ["Factor", "Analysis"],
    "rows": [["Market Conditions", "Competitive market..."]]
  }
}
```

Source: `transactions[].economic_circumstances`.

#### 6. Benchmark tables (`bm_{slug}_{table_id}`)

Key pattern: `bm_study_1_allocation`, `bm_study_1_search_results`, etc.
Table IDs: `allocation`, `search_strategy`, `search_results`, `adjustments`.

```json
{
  "auto_table": {
    "type": "search_results",
    "columns": ["Company", "Country", "TNMM", "Berry Ratio"],
    "rows": [["Comp A", "NL", "5.2%", "1.15"]]
  }
}
```

Source: `benchmarks[].tables[]` in data.json. Each table has `id`, `columns`, `rows`.

## general_notes

Optional array of note groups. Currently not rendered by the Workspace Editor but reserved for future use.

```json
[
  {
    "scope": "group",
    "title": "Acme Group",
    "items": ["Key deadline: March 2025"]
  }
]
```

## jurisdiction_svg

Optional. HTML string containing an SVG map highlighting the entity's country. Empty string if no map data available.

```html
<svg class="map-svg" viewBox="0 0 800 700" xmlns="http://www.w3.org/2000/svg">
  <path class="map-land" d="..."/>
  <path class="map-highlight" d="..."/>
</svg>
```

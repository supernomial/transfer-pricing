# View JSON Schema

Reference for producing view JSON consumed by the Preview (`combined_view.html`).

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

- Defaults: title = "Local File", subtitle = entity name, meta = "Transfer Pricing Documentation · FY {year}".
- `playbook_name`: read from the playbook's frontmatter `name` field. "Standard" for the built-in OECD playbook, custom name for user playbooks. Displayed in the Preview top bar.

## progress

```json
{
  "stage": "draft",
  "total_sections": 25
}
```

- `stage`: one of `"draft"`, `"review"`, `"final"`. From `local_files[].status`.

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
      "source_path": "executive-summary/objective",
      "scope": "universal",
      "color": "#64748b",
      "impact": "Applies to all local files"
    },
    "notes": ["Editorial note string"],
    "footnotes": ["Citation or footnote string"],
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
| `meta.source_path` | string | Content path derived from section title (e.g. `executive-summary/objective`). |
| `meta.scope` | string | `"universal"`, `"firm"`, `"group"`, or `"entity"`. |
| `meta.color` | string | Hex color for X-ray display. |
| `meta.impact` | string | Human-readable description of content scope. |
| `notes` | string[] | Editorial notes for this section. |
| `footnotes` | string[] | Citations or footnotes for this section. |
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

## jurisdiction_svg

Optional. HTML string containing an SVG map highlighting the entity's country. Empty string if no map data available.

```html
<svg class="map-svg" viewBox="0 0 800 700" xmlns="http://www.w3.org/2000/svg">
  <path class="map-land" d="..."/>
  <path class="map-highlight" d="..."/>
</svg>
```

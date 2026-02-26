#!/usr/bin/env python3
"""
Assemble a transfer pricing local file from records + blueprint.

This is the deterministic assembly script. It:
1. Reads the group records JSON (data.json with optional notes)
2. Reads the entity blueprint JSON (with optional section_notes)
3. Resolves @references/ and @library/ content references
4. Populates the template (LaTeX or HTML) with resolved values
5. For HTML: includes notes from records + blueprint in the preview
6. For PDF: compiles LaTeX via pdflatex
7. Saves output to the specified directory

Supports five output formats:
    --format pdf      → LaTeX → PDF (final deliverable)
    --format html     → HTML preview (live intake view in Cowork panel)
    --format report   → Annotated report view with X-ray mode (layer annotations)
    --format combined → Workspace Editor (full editor + notes + dashboard in one view)
    --format md       → Markdown preview (fallback)

Usage:
    python3 assemble_local_file.py \
        --data path/to/group.json \
        --blueprint path/to/blueprint.json \
        --references path/to/references/ \
        --library path/to/library/ \
        --template path/to/local_file.tex \
        --output path/to/output/dir/ \
        --format pdf

    python3 assemble_local_file.py \
        --data path/to/group.json \
        --blueprint path/to/blueprint.json \
        --references path/to/references/ \
        --library path/to/library/ \
        --template path/to/intake_preview.html \
        --output path/to/output/dir/ \
        --format html

Why a script and not Claude:
    - Deterministic: same input always produces same output
    - Token-efficient: no AI tokens spent on mechanical assembly
    - Fast to review: output is consistent, only data changes matter
    - Debuggable: inspect script logic if something looks wrong
"""

import argparse
import base64
import glob
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_frontmatter(text):
    """Strip YAML frontmatter from markdown content if present."""
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def load_json(path):
    """Load and return a JSON file."""
    if not os.path.exists(path):
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, 'r') as f:
        return json.load(f)


def resolve_reference(ref, references_dir, library_dir, group_content_dir=None, entity_content_dir=None):
    """Resolve a @references/, @library/, @group/, or @entity/ content reference to actual text.

    Resolution order:
        @references/  → plugin references dir (Layer 1 — universal)
        @library/     → firm library dir (Layer 2 — firm-wide)
        @group/       → group content dir (Layer 3 — group-specific)
        @entity/      → entity content dir (Layer 4 — entity-specific file)
        plain text    → returned as-is (Layer 4 — entity-specific)
    """
    if ref.startswith('@references/'):
        rel_path = ref.replace('@references/', '')
        for ext in ['.md', '.json', '.txt', '']:
            full_path = os.path.join(references_dir, rel_path + ext)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    return strip_frontmatter(f.read().strip())
        print(f"Warning: Could not resolve reference: {ref}", file=sys.stderr)
        return f"[UNRESOLVED: {ref}]"

    elif ref.startswith('@library/'):
        rel_path = ref.replace('@library/', '')
        for ext in ['.md', '.json', '.txt', '']:
            full_path = os.path.join(library_dir, rel_path + ext)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    return strip_frontmatter(f.read().strip())
        print(f"Warning: Could not resolve library reference: {ref}", file=sys.stderr)
        return f"[UNRESOLVED: {ref}]"

    elif ref.startswith('@group/'):
        if not group_content_dir:
            print(f"Warning: @group/ reference used but no --group-content dir provided: {ref}", file=sys.stderr)
            return f"[UNRESOLVED: {ref}]"
        rel_path = ref.replace('@group/', '')
        for ext in ['.md', '.json', '.txt', '']:
            full_path = os.path.join(group_content_dir, rel_path + ext)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    return strip_frontmatter(f.read().strip())
        print(f"Warning: Could not resolve group content reference: {ref}", file=sys.stderr)
        return f"[UNRESOLVED: {ref}]"

    elif ref.startswith('@entity/'):
        if not entity_content_dir:
            print(f"Warning: @entity/ reference used but no --entity-content dir provided: {ref}", file=sys.stderr)
            return f"[UNRESOLVED: {ref}]"
        rel_path = ref.replace('@entity/', '')
        for ext in ['.md', '.json', '.txt', '']:
            full_path = os.path.join(entity_content_dir, rel_path + ext)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    return strip_frontmatter(f.read().strip())
        print(f"Warning: Could not resolve entity content reference: {ref}", file=sys.stderr)
        return f"[UNRESOLVED: {ref}]"

    else:
        # Plain text, return as-is (Layer 4)
        return ref


def build_font_faces(brand_dir):
    """Build @font-face declarations with base64-embedded Graphik font files.

    Looks for woff2 files in brand_dir/fonts/. Returns CSS @font-face blocks
    or an empty string if no fonts are found (system font stack is the fallback).
    """
    fonts_dir = os.path.join(brand_dir, 'fonts')
    if not os.path.isdir(fonts_dir):
        return ''

    # Map filename patterns to CSS font-weight
    weight_map = {
        'Regular': '400',
        'Medium': '500',
        'Semibold': '600',
    }

    faces = []
    for weight_name, weight_value in weight_map.items():
        font_file = os.path.join(fonts_dir, f'Graphik-{weight_name}-Web.woff2')
        if not os.path.exists(font_file):
            continue
        with open(font_file, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('ascii')
        faces.append(
            f"@font-face {{\n"
            f"  font-family: 'Graphik';\n"
            f"  font-weight: {weight_value};\n"
            f"  font-style: normal;\n"
            f"  font-display: swap;\n"
            f"  src: url(data:font/woff2;base64,{encoded}) format('woff2');\n"
            f"}}"
        )

    if faces:
        print(f"Embedded {len(faces)} Graphik font weight(s)")
    return '\n\n'.join(faces)


def inject_brand_css(template_content, brand_path):
    """Read brand.css and inject it as a separate <style> block.

    Replaces the <!-- BRAND_CSS_INJECT --> HTML comment with a full
    <style>...</style> block. This keeps the template's own <style> tag
    free of placeholders so IDE linters don't flag it.
    Also resolves <<FONT_FACES>> inside brand.css with base64-encoded fonts.
    If brand.css is not found or no placeholder exists, returns template unchanged.

    Args:
        template_content: The HTML template string
        brand_path: Path to brand.css (top-level assets/brand.css)
    """
    if not os.path.exists(brand_path):
        print(f"Warning: brand.css not found at {brand_path}", file=sys.stderr)
        return template_content
    with open(brand_path, 'r') as f:
        brand_css = f.read()

    # Inject base64-encoded font faces (fonts/ is next to brand.css)
    if '<<FONT_FACES>>' in brand_css:
        brand_dir = os.path.dirname(brand_path)
        font_faces = build_font_faces(brand_dir)
        brand_css = brand_css.replace('<<FONT_FACES>>', font_faces)

    brand_block = f'<style>\n/* --- Brand design system --- */\n{brand_css}\n</style>'

    if '<!-- BRAND_CSS_INJECT -->' in template_content:
        return template_content.replace('<!-- BRAND_CSS_INJECT -->', brand_block)
    # Backwards compat: support old <<BRAND_CSS>> placeholder inside <style>
    if '<<BRAND_CSS>>' in template_content:
        return template_content.replace('<<BRAND_CSS>>', brand_css)
    return template_content


def classify_source(raw_value, section_key):
    """Determine which content layer a blueprint section value comes from.

    Returns a dict with layer info:
      layer: 1-4
      label: human-readable label
      source_path: original @reference or @library path (or None)
      scope: 'plugin' | 'firm' | 'group' | 'entity'
      color: CSS color for annotations (inline style fallback)

    IMPORTANT: The color values here MUST match --sn-layer1 through --sn-layer4
    in brand.css. If you change layer colors, update both places.
    """
    if isinstance(raw_value, str) and raw_value.startswith('@references/'):
        return {
            'layer': 1, 'label': 'Universal',
            'source_path': raw_value, 'scope': 'plugin',
            'color': '#64748b',  # brand.css --sn-layer1
            'impact': 'Standard content from Supernomial — updates with plugin upgrades'
        }
    elif isinstance(raw_value, str) and raw_value.startswith('@library/'):
        return {
            'layer': 2, 'label': 'Firm Library',
            'source_path': raw_value, 'scope': 'firm',
            'color': '#94a3b8',  # brand.css --sn-layer2
            'impact': 'From your firm library — shared across all clients'
        }
    elif isinstance(raw_value, str) and raw_value.startswith('@group/'):
        return {
            'layer': 3, 'label': 'Group',
            'source_path': raw_value, 'scope': 'group',
            'color': '#a855f7',  # brand.css --sn-layer3
            'impact': 'Group-wide — editing affects all local files in this group'
        }
    elif isinstance(raw_value, str) and raw_value.startswith('@entity/'):
        return {
            'layer': 4, 'label': 'Entity',
            'source_path': raw_value, 'scope': 'entity',
            'color': '#3b82f6',  # brand.css --sn-layer4
            'impact': 'Entity-specific — this report only'
        }
    else:
        # Plain text is entity-specific (Layer 4)
        return {
            'layer': 4, 'label': 'Entity',
            'source_path': None, 'scope': 'entity',
            'color': '#3b82f6',  # brand.css --sn-layer4
            'impact': 'Entity-specific — this report only'
        }


# ---------------------------------------------------------------------------
# Blueprint inheritance
# ---------------------------------------------------------------------------

def expand_dynamic_sections(template, blueprint):
    """Expand dynamic markers in template sections using blueprint data.

    Walks the template's sections tree. When a node has a 'dynamic' field:
      - "functional-profiles": keep the node as a container, generate children
        from blueprint's covered_profiles + dynamic_templates
      - "transactions": keep the node as a container, generate children
        from blueprint's covered_transactions + dynamic_templates

    The dynamic node is KEPT (preserving its heading) and gets generated
    children — it does not get replaced.

    Returns expanded sections as a chapters-format array.
    """
    import copy
    sections = copy.deepcopy(template.get('sections', []))
    dynamic_templates = template.get('dynamic_templates', {})

    def make_title(slug):
        """Convert kebab-case slug to title case: 'full-fledged-distributor' → 'Full-Fledged Distributor'."""
        return slug.replace('-', ' ').title()

    def expand_node(node):
        dynamic = node.get('dynamic')
        if not dynamic or not isinstance(dynamic, str):
            # Recurse into children
            if 'children' in node:
                expanded_children = []
                for child in node['children']:
                    expanded_children.extend(expand_node(child))
                node['children'] = expanded_children
            return [node]

        if dynamic == 'functional-profiles':
            items = blueprint.get('covered_profiles', [])
            dt = dynamic_templates.get('functional-profiles', {})
        elif dynamic == 'transactions':
            items = blueprint.get('covered_transactions', [])
            dt = dynamic_templates.get('transactions', {})
        else:
            return [node]

        id_pattern = dt.get('id_pattern', '{id}')
        child_templates = dt.get('children', [])

        expanded_children = []
        for item in items:
            item_id = item if isinstance(item, str) else item.get('id', '')
            item_title = item if isinstance(item, str) else item.get('title', item_id)
            # Use title from item if provided, otherwise derive from slug
            display_title = item_title if not isinstance(item, str) else make_title(item_id)

            new_child = {
                'id': id_pattern.replace('{id}', item_id),
                'title': display_title,
            }

            if child_templates:
                children = []
                for ct in child_templates:
                    child = copy.deepcopy(ct)
                    children.append(child)
                new_child['children'] = children

            expanded_children.append(new_child)

        # Keep the parent node, set generated items as its children
        node.pop('dynamic', None)
        node['children'] = expanded_children
        return [node]

    result = []
    for section in sections:
        result.extend(expand_node(section))
    return result


def apply_title_overrides(chapters, title_overrides):
    """Walk chapters tree and apply title overrides by path.

    Path is built by joining ancestor ids with '/'.
    E.g., "economic-analysis/functional-analysis/fp-full-fledged-distributor"
    Mutates chapters in place.
    """
    if not title_overrides:
        return

    def walk(nodes, parent_path=''):
        for node in nodes:
            node_id = node.get('id', '')
            path = f"{parent_path}/{node_id}" if parent_path else node_id
            if path in title_overrides:
                node['title'] = title_overrides[path]
            children = node.get('children', [])
            if children:
                walk(children, path)

    walk(chapters)


def bridge_to_legacy(blueprint, chapters):
    """Convert new-format blueprint (content path-keys + chapters tree) to legacy format.

    Produces:
      - sections{}: flat dict with underscore keys from content path-keys
      - chapters[]: old-format array with id/title/sections(id/title/keys/subsections)
      - section_notes{}: empty dict (placeholder)
      - footnotes{}: empty dict (placeholder)

    Path key conversion: "executive-summary/objective" → "executive_summary_objective"
    (replace both '-' and '/' with '_')
    """
    content = blueprint.get('content', {})

    # Build flat sections dict from content path-keys
    sections = {}
    for path_key, value in content.items():
        flat_key = path_key.replace('-', '_').replace('/', '_')
        if isinstance(value, list) and len(value) == 1:
            sections[flat_key] = value[0]
        else:
            sections[flat_key] = value

    # Build old-format chapters array from expanded chapters tree
    def build_keys_for_path(path_prefix, include_descendants=False):
        """Find content keys matching this section path.

        By default, returns only the exact match (child paths go to child nodes).
        With include_descendants=True, also returns keys for all descendant paths.
        Use include_descendants at max depth (subsection level) where the legacy
        format can't represent deeper nesting.
        """
        flat_prefix = path_prefix.replace('-', '_').replace('/', '_')
        if not include_descendants:
            if flat_prefix in sections:
                return [flat_prefix]
            return []
        # Collect this key + all descendant keys
        keys = []
        for path_key in content:
            flat = path_key.replace('-', '_').replace('/', '_')
            if flat == flat_prefix or flat.startswith(flat_prefix + '_'):
                keys.append(flat)
        return keys

    def convert_node(node, parent_path='', depth=0):
        """Convert a chapters-tree node to legacy format."""
        node_id = node.get('id', '')
        path = f"{parent_path}/{node_id}" if parent_path else node_id
        children = node.get('children', [])

        result = {
            'id': node_id,
            'title': node.get('title', ''),
        }

        if depth == 0:
            # Top-level = chapter → has 'sections'
            result['sections'] = []
            if children:
                for child in children:
                    result['sections'].append(convert_node(child, path, depth + 1))
            else:
                # Leaf chapter — keys directly
                result['keys'] = build_keys_for_path(path)
        elif depth == 1:
            # Level 2 = section → has 'keys' and optionally 'subsections'
            sub_children = [c for c in children if c.get('children')]
            leaf_children = [c for c in children if not c.get('children')]

            if sub_children or leaf_children:
                result['keys'] = build_keys_for_path(path)
                # Only include keys that are direct (not belonging to subsections)
                if children:
                    result['subsections'] = []
                    for child in children:
                        result['subsections'].append(convert_node(child, path, depth + 1))
            else:
                result['keys'] = build_keys_for_path(path)
        else:
            # Level 3+ = subsection → collect keys for this path and all descendants
            # (legacy format can't represent deeper nesting, so roll up)
            result['keys'] = build_keys_for_path(path, include_descendants=True)

        return result

    legacy_chapters = []
    for node in chapters:
        legacy_chapters.append(convert_node(node, '', 0))

    # Build result: all original fields + generated legacy fields
    result = dict(blueprint)
    result['chapters'] = legacy_chapters
    result['sections'] = sections
    result.setdefault('section_notes', {})
    result.setdefault('footnotes', {})
    # Remove new-format-only fields that downstream doesn't need
    result.pop('content', None)
    result.pop('based_on', None)
    result.pop('covered_profiles', None)
    result.pop('covered_transactions', None)
    result.pop('title_overrides', None)

    return result


def resolve_blueprint_inheritance(blueprint, references_dir, library_dir, blueprints_dir=None):
    """Resolve blueprint inheritance via 'based_on' field.

    If blueprint has no 'based_on', returns it unchanged.
    Otherwise loads the template, expands dynamic sections,
    applies title overrides, and bridges to legacy format.

    Template search order:
      1. references_dir/blueprints/{name}.json  (universal)
      2. library_dir/blueprints/{name}.json     (firm)
      3. blueprints_dir/template-{name}.json    (group)
    """
    based_on = blueprint.get('based_on')
    if not based_on:
        return blueprint

    # Load template
    template = None
    search_paths = [
        os.path.join(references_dir, 'blueprints', f'{based_on}.json'),
        os.path.join(library_dir, 'blueprints', f'{based_on}.json'),
    ]
    if blueprints_dir:
        search_paths.append(os.path.join(blueprints_dir, f'template-{based_on}.json'))

    for path in search_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                template = json.load(f)
            print(f"Loaded blueprint template: {path}")
            break

    if template is None:
        print(f"Warning: Could not find blueprint template '{based_on}'. Searched:", file=sys.stderr)
        for p in search_paths:
            print(f"  {p}", file=sys.stderr)
        return blueprint

    # Expand dynamic sections
    chapters = expand_dynamic_sections(template, blueprint)

    # Apply title overrides
    apply_title_overrides(chapters, blueprint.get('title_overrides', {}))

    # Bridge to legacy format
    result = bridge_to_legacy(blueprint, chapters)

    return result


def resolve_blueprint_sections(blueprint, references_dir, library_dir, group_content_dir=None, entity_content_dir=None):
    """Resolve all content references in a blueprint's sections.

    Section values can be:
      - string: resolved as a single reference or plain text
      - array: each element resolved independently, joined with double newlines
    """
    resolved = {}
    sections = blueprint.get('sections', {})
    for key, value in sections.items():
        if isinstance(value, list):
            parts = []
            for element in value:
                if isinstance(element, str):
                    parts.append(resolve_reference(element, references_dir, library_dir, group_content_dir, entity_content_dir))
                else:
                    parts.append(str(element))
            resolved[key] = '\n\n'.join(parts)
        elif isinstance(value, str):
            resolved[key] = resolve_reference(value, references_dir, library_dir, group_content_dir, entity_content_dir)
        else:
            resolved[key] = value
    return resolved


def resolve_blueprint_sections_with_meta(blueprint, references_dir, library_dir, group_content_dir=None, entity_content_dir=None):
    """Resolve all content references and track source layer metadata.

    Returns two dicts:
      resolved: {section_key: resolved_text}
      meta: {section_key: meta_dict_or_list}

    For string sections: meta is a single dict {layer, label, source_path, scope, color, impact}
    For array sections: meta is a list of dicts (one per element), and a composite
      summary is added. The first element is treated as the primary layer for display.
    """
    resolved = {}
    meta = {}
    sections = blueprint.get('sections', {})
    for key, value in sections.items():
        if isinstance(value, list):
            parts = []
            part_metas = []
            for element in value:
                if isinstance(element, str):
                    parts.append(resolve_reference(element, references_dir, library_dir, group_content_dir, entity_content_dir))
                    part_metas.append(classify_source(element, key))
                else:
                    parts.append(str(element))
                    part_metas.append(classify_source('', key))
            resolved[key] = '\n\n'.join(parts)
            # Build composite meta: use first element as primary, note all layers
            primary = part_metas[0] if part_metas else classify_source('', key)
            layer_labels = list(dict.fromkeys(m['label'] for m in part_metas))
            meta[key] = {
                'layer': primary['layer'],
                'label': primary['label'],
                'source_path': primary.get('source_path'),
                'scope': primary['scope'],
                'color': primary['color'],
                'impact': primary['impact'],
                'composite': True,
                'composite_labels': layer_labels,
                'parts': part_metas
            }
        elif isinstance(value, str):
            resolved[key] = resolve_reference(value, references_dir, library_dir, group_content_dir, entity_content_dir)
            meta[key] = classify_source(value, key)
        else:
            resolved[key] = value
            meta[key] = classify_source('', key)
    return resolved, meta


# ---------------------------------------------------------------------------
# Records lookups
# ---------------------------------------------------------------------------

def find_entity(data, entity_id):
    """Find an entity by ID in the records."""
    for entity in data.get('entities', []):
        if entity.get('id') == entity_id:
            return entity
    print(f"Error: Entity '{entity_id}' not found in records.", file=sys.stderr)
    available = [e.get('id') for e in data.get('entities', [])]
    if available:
        print(f"  Available entities: {', '.join(available)}", file=sys.stderr)
    sys.exit(1)


def get_entity_transactions(data, entity_id):
    """Get all transactions involving this entity."""
    transactions = []
    for tx in data.get('transactions', []):
        if tx.get('from_entity') == entity_id or tx.get('to_entity') == entity_id:
            transactions.append(tx)
    return transactions


# ---------------------------------------------------------------------------
# LaTeX helpers
# ---------------------------------------------------------------------------

def escape_latex(text):
    """Escape special LaTeX characters in text."""
    if not isinstance(text, str):
        return str(text)
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def format_amount(amount):
    """Format a number with thousand separators."""
    if isinstance(amount, (int, float)):
        return f"{amount:,.0f}"
    return str(amount)


def build_transaction_rows(transactions):
    """Build LaTeX table rows from transaction data."""
    if not transactions:
        return "No controlled transactions recorded & --- \\\\"
    rows = []
    for tx in transactions:
        name = escape_latex(tx.get('name', 'Unknown'))
        amount = format_amount(tx.get('amount', 0))
        rows.append(f"{name} & {amount} \\\\")
    return '\n'.join(rows)


def slugify(text):
    """Convert text to a filesystem-safe slug.

    Strips dots (B.V., Ltd., GmbH.) to avoid confusing file viewers
    that interpret dots as extension separators.
    """
    text = text.strip()
    text = text.replace(' ', '_')
    text = text.replace('.', '')    # B.V. -> BV, Ltd. -> Ltd
    text = re.sub(r'[^\w\-]', '', text)
    return text


# ---------------------------------------------------------------------------
# LaTeX report body builder
# ---------------------------------------------------------------------------

def render_generic_table_latex(table_obj, transactions):
    """Render a benchmark table object as a LaTeX tabularx table.

    Each table_obj has:
        columns: list of header strings
        rows: dict keyed by transaction ID, values are arrays
        label: optional table label
    """
    columns = table_obj.get('columns', [])
    rows = table_obj.get('rows', {})
    label = table_obj.get('label', '')

    if not columns or not rows:
        return ''

    ncols = len(columns)
    col_spec = 'l' + 'X' * (ncols - 1) if ncols > 1 else 'X'
    parts = []
    parts.append(f'\\begin{{tabularx}}{{\\textwidth}}{{{col_spec}}}')
    parts.append('\\toprule')
    header = ' & '.join(escape_latex(c) for c in columns) + ' \\\\'
    parts.append(header)
    parts.append('\\midrule')

    for tx_id, row_values in rows.items():
        cells = []
        for val in row_values:
            if isinstance(val, (int, float)):
                cells.append(format_amount(val) if isinstance(val, int) and val > 999 else str(val))
            else:
                cells.append(escape_latex(str(val)))
        parts.append(' & '.join(cells) + ' \\\\')

    parts.append('\\bottomrule')
    parts.append('\\end{tabularx}')

    return '\n'.join(parts)


def build_auto_table_latex(key, data, entity_id, transactions, blueprint):
    """Generate LaTeX table content for auto-type sections.

    Returns a LaTeX string for the specified auto section key.
    """

    # --- Preamble: transactions overview ---
    if key == 'preamble_transactions_overview':
        covered_ids = []
        for lf in data.get('local_files', []):
            if lf.get('entity') == entity_id:
                covered_ids = lf.get('covered_transactions', [])
                break
        covered_txs = [tx for tx in data.get('transactions', []) if tx['id'] in covered_ids]
        if not covered_txs:
            covered_txs = transactions

        parts = []
        parts.append('\\begin{tabularx}{\\textwidth}{XllXr}')
        parts.append('\\toprule')
        parts.append('Description & From & To & Currency & Amount \\\\')
        parts.append('\\midrule')
        for tx in covered_txs:
            desc = escape_latex(tx.get('name', ''))
            from_name = tx.get('from_entity', '')
            to_name = tx.get('to_entity', '')
            for e in data.get('entities', []):
                if e['id'] == tx.get('from_entity'):
                    from_name = e.get('name', from_name)
                if e['id'] == tx.get('to_entity'):
                    to_name = e.get('name', to_name)
            currency = escape_latex(tx.get('currency', ''))
            amount = format_amount(tx.get('amount', 0))
            parts.append(f'{desc} & {escape_latex(from_name)} & {escape_latex(to_name)} & {currency} & {amount} \\\\')
        parts.append('\\bottomrule')
        parts.append('\\end{tabularx}')
        return '\n'.join(parts)

    # --- Transaction-level auto tables ---
    tx_match = re.match(r'^tx_(\d+)_(.+)$', key)
    if tx_match:
        tx_num = tx_match.group(1)
        sub_key = tx_match.group(2)
        tx_id_hyphen = f'tx-{tx_num}'
        tx = None
        for t in data.get('transactions', []):
            if t['id'] == tx_id_hyphen:
                tx = t
                break
        if not tx:
            return f'% Transaction {tx_id_hyphen} not found'

        tx_type = tx.get('transaction_type', '')
        is_financial = tx_type in FINANCIAL_TYPES

        if sub_key == 'contractual_terms':
            ct = tx.get('contractual_terms', {})
            if not ct:
                return ''
            if is_financial:
                # Transposed table: each row is a property, columns are the terms
                term_keys = list(ct.keys())
                parts = []
                ncols = len(term_keys)
                col_spec = 'X' * ncols if ncols > 0 else 'X'
                parts.append(f'\\begin{{tabularx}}{{\\textwidth}}{{{col_spec}}}')
                parts.append('\\toprule')
                parts.append(' & '.join(escape_latex(k.replace('_', ' ').title()) for k in term_keys) + ' \\\\')
                parts.append('\\midrule')
                parts.append(' & '.join(escape_latex(str(ct[k])) for k in term_keys) + ' \\\\')
                parts.append('\\bottomrule')
                parts.append('\\end{tabularx}')
                return '\n'.join(parts)
            else:
                # Standard table: key-value rows
                parts = []
                parts.append('\\begin{tabularx}{\\textwidth}{lX}')
                parts.append('\\toprule')
                parts.append('Term & Detail \\\\')
                parts.append('\\midrule')
                for k, v in ct.items():
                    parts.append(f'{escape_latex(k.replace("_", " ").title())} & {escape_latex(str(v))} \\\\')
                parts.append('\\bottomrule')
                parts.append('\\end{tabularx}')
                return '\n'.join(parts)

        if sub_key == 'characteristics':
            if is_financial:
                return ''
            chars = tx.get('characteristics', {})
            if not chars:
                return ''
            parts = []
            parts.append('\\begin{tabularx}{\\textwidth}{lX}')
            parts.append('\\toprule')
            parts.append('Characteristic & Description \\\\')
            parts.append('\\midrule')
            for k, v in chars.items():
                parts.append(f'{escape_latex(k.replace("_", " ").title())} & {escape_latex(str(v))} \\\\')
            parts.append('\\bottomrule')
            parts.append('\\end{tabularx}')
            return '\n'.join(parts)

        if sub_key == 'economic_circumstances':
            ec = tx.get('economic_circumstances', {})
            if not ec:
                return ''
            parts = []
            parts.append('\\begin{tabularx}{\\textwidth}{lX}')
            parts.append('\\toprule')
            parts.append('Factor & Analysis \\\\')
            parts.append('\\midrule')
            for k, v in ec.items():
                parts.append(f'{escape_latex(k.replace("_", " ").title())} & {escape_latex(str(v))} \\\\')
            parts.append('\\bottomrule')
            parts.append('\\end{tabularx}')
            return '\n'.join(parts)

    # --- Benchmark auto tables ---
    bm_match = re.match(r'^bm_(.+?)_(allocation|search_strategy|search_results|adjustments)$', key)
    if bm_match:
        bm_slug = bm_match.group(1)
        table_id = bm_match.group(2)
        bm_id_hyphen = bm_slug.replace('_', '-')
        bm = None
        for b in data.get('benchmarks', []):
            if b['id'] == bm_id_hyphen:
                bm = b
                break
        if not bm:
            return f'% Benchmark {bm_id_hyphen} not found'
        for table_obj in bm.get('tables', []):
            if table_obj.get('id') == table_id:
                return render_generic_table_latex(table_obj, transactions)
        return f'% Table {table_id} not found in benchmark {bm_id_hyphen}'

    # --- Transactions not covered ---
    if key == 'transactions_not_covered':
        covered_ids = set()
        for lf in data.get('local_files', []):
            if lf.get('entity') == entity_id:
                covered_ids = set(lf.get('covered_transactions', []))
                break
        if not covered_ids:
            covered_ids = {tx['id'] for tx in transactions}

        all_entity_txs = get_entity_transactions(data, entity_id)
        not_covered = [tx for tx in all_entity_txs if tx['id'] not in covered_ids]

        if not not_covered:
            return 'No additional intercompany transactions were identified for the tested entity that are not covered in this documentation.'

        parts = []
        parts.append('\\begin{tabularx}{\\textwidth}{Xllr}')
        parts.append('\\toprule')
        parts.append('Transaction & Counterparty & Type & Amount \\\\')
        parts.append('\\midrule')
        for tx in not_covered:
            name = escape_latex(tx.get('name', ''))
            cp_id = tx.get('to_entity') if tx.get('from_entity') == entity_id else tx.get('from_entity')
            cp_name = cp_id
            for e in data.get('entities', []):
                if e['id'] == cp_id:
                    cp_name = e.get('name', cp_id)
                    break
            tx_type = humanize_transaction_type(tx.get('transaction_type', ''))
            amount = format_amount(tx.get('amount', 0))
            parts.append(f'{name} & {escape_latex(cp_name)} & {escape_latex(tx_type)} & {amount} \\\\')
        parts.append('\\bottomrule')
        parts.append('\\end{tabularx}')
        return '\n'.join(parts)

    return f'% Unknown auto section: {key}'


def is_auto_section(key):
    """Check if a section key refers to an auto-generated table section."""
    if key == 'preamble_transactions_overview':
        return True
    if key == 'transactions_not_covered':
        return True
    tx_match = re.match(r'^tx_\d+_(contractual_terms|characteristics|economic_circumstances)$', key)
    if tx_match:
        return True
    bm_match = re.match(r'^bm_.+_(allocation|search_strategy|search_results|adjustments)$', key)
    if bm_match:
        return True
    return False


def build_report_body_latex(blueprint, resolved_sections, data, entity, transactions):
    """Build the complete LaTeX report body from blueprint sections.

    Organizes sections into the PDF chapter structure:
    1. Executive Summary (preamble sections)
    2. Business Description
    3. Industry Analysis
    4. Economic Analysis (functional profiles, controlled transactions, benchmarks)
    5. Closing
    """
    entity_id = entity.get('id', '')
    entity_name = entity.get('name', '')
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', ''))

    parts = []

    def render_section_content(key):
        """Render a single section's content as LaTeX."""
        if is_auto_section(key):
            return build_auto_table_latex(key, data, entity_id, transactions, blueprint)
        text = resolved_sections.get(key, '')
        if is_section_complete(text):
            return escape_latex(text)
        return escape_latex(f'[{humanize_section_key(key)} -- pending]')

    chapters = blueprint.get('chapters', [])

    if chapters:
        # --- New path: iterate chapters array from blueprint (3-level) ---
        for chapter in chapters:
            chapter_title = chapter.get('title', '')
            parts.append(f'\\section{{{escape_latex(chapter_title)}}}')

            for section in chapter.get('sections', []):
                # Legacy flat key format
                if isinstance(section, str):
                    key = section
                    label = humanize_section_key(key)
                    parts.append(f'\\subsection{{{escape_latex(label)}}}')
                    parts.append(render_section_content(key))
                    parts.append('')
                    if key.endswith('_intro'):
                        auto_suffix = key[:-len('_intro')]
                        if auto_suffix != key and is_auto_section(auto_suffix):
                            parts.append(render_section_content(auto_suffix))
                            parts.append('')
                    continue

                # New format: section object
                sec_title = section.get('title', '')
                sec_keys = section.get('keys', [])
                subsections = section.get('subsections', [])

                parts.append(f'\\subsection{{{escape_latex(sec_title)}}}')

                for key in sec_keys:
                    parts.append(render_section_content(key))
                    parts.append('')
                    if key.endswith('_intro'):
                        auto_suffix = key[:-len('_intro')]
                        if auto_suffix != key and is_auto_section(auto_suffix):
                            parts.append(render_section_content(auto_suffix))
                            parts.append('')

                for subsec in subsections:
                    subsec_title = subsec.get('title', '')
                    subsec_keys = subsec.get('keys', [])
                    parts.append(f'\\subsubsection{{{escape_latex(subsec_title)}}}')

                    for key in subsec_keys:
                        parts.append(render_section_content(key))
                        parts.append('')
                        if key.endswith('_intro'):
                            auto_suffix = key[:-len('_intro')]
                            if auto_suffix != key and is_auto_section(auto_suffix):
                                parts.append(render_section_content(auto_suffix))
                                parts.append('')

    else:
        # --- Fallback: prefix-based categorization (backward compat) ---

        # Collect all section keys from the blueprint
        all_keys = list(blueprint.get('sections', {}).keys())

        # Also include auto keys that aren't in blueprint sections
        auto_keys_to_add = ['preamble_transactions_overview', 'transactions_not_covered']
        for tx in transactions:
            tx_key = tx['id'].replace('-', '_')
            tx_type = tx.get('transaction_type', '')
            is_financial = tx_type in FINANCIAL_TYPES
            auto_keys_to_add.append(f'{tx_key}_contractual_terms')
            if not is_financial:
                auto_keys_to_add.append(f'{tx_key}_characteristics')
            auto_keys_to_add.append(f'{tx_key}_economic_circumstances')
        for bm in data.get('benchmarks', []):
            bm_key = bm['id'].replace('-', '_')
            # Only include benchmarks used by covered transactions
            bm_tx_ids = set(bm.get('transactions', []))
            covered_tx_ids = {tx['id'] for tx in transactions}
            if bm_tx_ids & covered_tx_ids:
                for table_id in ['allocation', 'search_strategy', 'search_results', 'adjustments']:
                    auto_keys_to_add.append(f'bm_{bm_key}_{table_id}')

        # Merge auto keys into the full key set (for categorization)
        full_keys = list(all_keys)
        for k in auto_keys_to_add:
            if k not in full_keys:
                full_keys.append(k)

        # Categorize all keys
        categorized = OrderedDict()
        for key in full_keys:
            cat_id, cat_label = categorize_section(key)
            if cat_id not in categorized:
                categorized[cat_id] = []
            categorized[cat_id].append(key)

        # --- 1. Executive Summary ---
        parts.append('\\section{Executive Summary}')
        preamble_keys = categorized.get('preamble', [])
        business_keys_for_preamble = categorized.get('business', [])

        # Preamble content sections
        for key in preamble_keys:
            label = humanize_section_key(key)
            parts.append(f'\\subsection{{{escape_latex(label)}}}')
            parts.append(render_section_content(key))
            parts.append('')

        # --- 2. Business Description ---
        parts.append('\\section{Business Description}')
        for key in business_keys_for_preamble:
            label = humanize_section_key(key)
            parts.append(f'\\subsection{{{escape_latex(label)}}}')
            parts.append(render_section_content(key))
            parts.append('')

        # --- 3. Industry Analysis ---
        industry_keys = categorized.get('industry', [])
        if industry_keys:
            parts.append('\\section{Industry Analysis}')
            for key in industry_keys:
                label = humanize_section_key(key)
                parts.append(f'\\subsection{{{escape_latex(label)}}}')
                parts.append(render_section_content(key))
                parts.append('')

        # --- 4. Economic Analysis ---
        parts.append('\\section{Economic Analysis}')

        # 4a. Functional Analysis
        fp_keys = categorized.get('functional', [])
        if fp_keys:
            parts.append('\\subsection{Functional Analysis}')
            # Group by profile slug
            profiles = OrderedDict()
            for key in fp_keys:
                # fp_{slug}_{block} — extract slug
                match = re.match(r'^fp_(.+?)_(overview|functions|assets|risks)$', key)
                if match:
                    slug = match.group(1)
                    if slug not in profiles:
                        profiles[slug] = []
                    profiles[slug].append(key)
                else:
                    profiles.setdefault('_other', []).append(key)

            for slug, keys in profiles.items():
                profile_name = slug.replace('_', ' ').title()
                parts.append(f'\\subsubsection{{{escape_latex(profile_name)}}}')
                for key in keys:
                    block_label = humanize_section_key(key)
                    parts.append(f'\\paragraph{{{escape_latex(block_label)}}}')
                    parts.append(render_section_content(key))
                    parts.append('')

        # 4b. Controlled Transactions
        tx_keys = categorized.get('transactions', [])
        if tx_keys:
            parts.append('\\subsection{Controlled Transactions}')

            # Group transactions by transaction_type
            tx_by_type = OrderedDict()
            for key in tx_keys:
                tx_match = re.match(r'^tx_(\d+)_', key)
                if tx_match:
                    tx_num = tx_match.group(1)
                    tx_id_hyphen = f'tx-{tx_num}'
                    tx_type = ''
                    for tx in data.get('transactions', []):
                        if tx['id'] == tx_id_hyphen:
                            tx_type = tx.get('transaction_type', '')
                            break
                    type_label = humanize_transaction_type(tx_type)
                    if type_label not in tx_by_type:
                        tx_by_type[type_label] = []
                    tx_by_type[type_label].append(key)

            for type_label, keys in tx_by_type.items():
                parts.append(f'\\subsubsection{{{escape_latex(type_label)}}}')
                for key in keys:
                    section_label = humanize_section_key(key)
                    parts.append(f'\\paragraph{{{escape_latex(section_label)}}}')
                    parts.append(render_section_content(key))
                    parts.append('')

        # 4c. Benchmark Application
        bm_keys = categorized.get('benchmark', [])
        if bm_keys:
            parts.append('\\subsection{Benchmark Application}')

            # Build list of known benchmark slugs from data
            known_bm_slugs = [bm['id'].replace('-', '_') for bm in data.get('benchmarks', [])]

            # Group by benchmark slug
            benchmarks = OrderedDict()
            for key in bm_keys:
                # Strip 'bm_' prefix and match against known benchmark slugs
                rest = key[3:]  # Remove 'bm_'
                matched_slug = None
                for slug in known_bm_slugs:
                    if rest.startswith(slug + '_') or rest == slug:
                        matched_slug = slug
                        break
                if not matched_slug:
                    # Fallback: take everything up to last known suffix
                    matched_slug = rest.rsplit('_', 1)[0] if '_' in rest else rest
                if matched_slug not in benchmarks:
                    benchmarks[matched_slug] = []
                benchmarks[matched_slug].append(key)

            for slug, keys in benchmarks.items():
                # Look up benchmark name
                bm_id_hyphen = slug.replace('_', '-')
                bm_name = slug.replace('_', ' ').title()
                for bm in data.get('benchmarks', []):
                    if bm['id'] == bm_id_hyphen:
                        bm_name = bm.get('name', bm_name)
                        break
                parts.append(f'\\subsubsection{{{escape_latex(bm_name)}}}')
                for key in keys:
                    section_label = humanize_section_key(key)
                    parts.append(f'\\paragraph{{{escape_latex(section_label)}}}')
                    parts.append(render_section_content(key))
                    parts.append('')

        # --- 5. Closing ---
        closing_keys = categorized.get('closing', [])
        if closing_keys:
            parts.append('\\section{Closing}')
            for key in closing_keys:
                label = humanize_section_key(key)
                parts.append(f'\\subsection{{{escape_latex(label)}}}')
                parts.append(render_section_content(key))
                parts.append('')

    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# HTML auto-table builder
# ---------------------------------------------------------------------------

def build_auto_table_html(key, data, entity_id, transactions, blueprint):
    """Generate HTML tables for auto-type sections.

    Mirrors build_auto_table_latex but produces HTML output for
    the report view and editor.
    """

    # --- Preamble: transactions overview ---
    if key == 'preamble_transactions_overview':
        covered_ids = []
        for lf in data.get('local_files', []):
            if lf.get('entity') == entity_id:
                covered_ids = lf.get('covered_transactions', [])
                break
        covered_txs = [tx for tx in data.get('transactions', []) if tx['id'] in covered_ids]
        if not covered_txs:
            covered_txs = transactions

        rows_html = []
        for tx in covered_txs:
            desc = escape_html(tx.get('name', ''))
            from_name = tx.get('from_entity', '')
            to_name = tx.get('to_entity', '')
            for e in data.get('entities', []):
                if e['id'] == tx.get('from_entity'):
                    from_name = e.get('name', from_name)
                if e['id'] == tx.get('to_entity'):
                    to_name = e.get('name', to_name)
            currency = escape_html(tx.get('currency', ''))
            amount = format_amount(tx.get('amount', 0))
            rows_html.append(
                f'<tr><td>{desc}</td><td>{escape_html(from_name)}</td>'
                f'<td>{escape_html(to_name)}</td><td>{currency}</td>'
                f'<td style="text-align:right">{amount}</td></tr>'
            )

        return (
            '<table class="doc-table"><thead><tr>'
            '<th>Description</th><th>From</th><th>To</th><th>Currency</th><th>Amount</th>'
            '</tr></thead><tbody>'
            + '\n'.join(rows_html)
            + '</tbody></table>'
        )

    # --- Transaction-level auto tables ---
    tx_match = re.match(r'^tx_(\d+)_(.+)$', key)
    if tx_match:
        tx_num = tx_match.group(1)
        sub_key = tx_match.group(2)
        tx_id_hyphen = f'tx-{tx_num}'
        tx = None
        for t in data.get('transactions', []):
            if t['id'] == tx_id_hyphen:
                tx = t
                break
        if not tx:
            return ''

        tx_type = tx.get('transaction_type', '')
        is_financial = tx_type in FINANCIAL_TYPES

        if sub_key == 'contractual_terms':
            ct = tx.get('contractual_terms', {})
            if not ct:
                return ''
            if is_financial:
                header = ''.join(f'<th>{escape_html(k.replace("_", " ").title())}</th>' for k in ct)
                row = ''.join(f'<td>{escape_html(str(v))}</td>' for v in ct.values())
                return f'<table class="doc-table"><thead><tr>{header}</tr></thead><tbody><tr>{row}</tr></tbody></table>'
            else:
                rows = ''.join(
                    f'<tr><td><strong>{escape_html(k.replace("_", " ").title())}</strong></td>'
                    f'<td>{escape_html(str(v))}</td></tr>'
                    for k, v in ct.items()
                )
                return f'<table class="doc-table"><thead><tr><th>Term</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>'

        if sub_key == 'characteristics':
            if is_financial:
                return ''
            chars = tx.get('characteristics', {})
            if not chars:
                return ''
            rows = ''.join(
                f'<tr><td><strong>{escape_html(k.replace("_", " ").title())}</strong></td>'
                f'<td>{escape_html(str(v))}</td></tr>'
                for k, v in chars.items()
            )
            return f'<table class="doc-table"><thead><tr><th>Characteristic</th><th>Description</th></tr></thead><tbody>{rows}</tbody></table>'

        if sub_key == 'economic_circumstances':
            ec = tx.get('economic_circumstances', {})
            if not ec:
                return ''
            rows = ''.join(
                f'<tr><td><strong>{escape_html(k.replace("_", " ").title())}</strong></td>'
                f'<td>{escape_html(str(v))}</td></tr>'
                for k, v in ec.items()
            )
            return f'<table class="doc-table"><thead><tr><th>Factor</th><th>Analysis</th></tr></thead><tbody>{rows}</tbody></table>'

    # --- Benchmark auto tables ---
    bm_match = re.match(r'^bm_(.+?)_(allocation|search_strategy|search_results|adjustments)$', key)
    if bm_match:
        bm_slug = bm_match.group(1)
        table_id = bm_match.group(2)
        bm_id_hyphen = bm_slug.replace('_', '-')
        bm = None
        for b in data.get('benchmarks', []):
            if b['id'] == bm_id_hyphen:
                bm = b
                break
        if not bm:
            return ''
        for table_obj in bm.get('tables', []):
            if table_obj.get('id') == table_id:
                columns = table_obj.get('columns', [])
                rows = table_obj.get('rows', {})
                header = ''.join(f'<th>{escape_html(c)}</th>' for c in columns)
                body = ''
                for tx_id, vals in rows.items():
                    cells = ''.join(f'<td>{escape_html(str(v))}</td>' for v in vals)
                    body += f'<tr>{cells}</tr>'
                return f'<table class="doc-table"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'
        return ''

    # --- Transactions not covered ---
    if key == 'transactions_not_covered':
        covered_ids = set()
        for lf in data.get('local_files', []):
            if lf.get('entity') == entity_id:
                covered_ids = set(lf.get('covered_transactions', []))
                break
        if not covered_ids:
            covered_ids = {tx['id'] for tx in transactions}

        all_entity_txs = get_entity_transactions(data, entity_id)
        not_covered = [tx for tx in all_entity_txs if tx['id'] not in covered_ids]

        if not not_covered:
            return '<p>No additional intercompany transactions were identified for the tested entity that are not covered in this documentation.</p>'

        rows = ''
        for tx in not_covered:
            name = escape_html(tx.get('name', ''))
            cp_id = tx.get('to_entity') if tx.get('from_entity') == entity_id else tx.get('from_entity')
            cp_name = cp_id
            for e in data.get('entities', []):
                if e['id'] == cp_id:
                    cp_name = e.get('name', cp_id)
                    break
            tx_type = humanize_transaction_type(tx.get('transaction_type', ''))
            amount = format_amount(tx.get('amount', 0))
            rows += f'<tr><td>{name}</td><td>{escape_html(cp_name)}</td><td>{escape_html(tx_type)}</td><td style="text-align:right">{amount}</td></tr>'

        return (
            '<table class="doc-table"><thead><tr>'
            '<th>Transaction</th><th>Counterparty</th><th>Type</th><th>Amount</th>'
            '</tr></thead><tbody>'
            + rows
            + '</tbody></table>'
        )

    return ''


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def build_transaction_rows_md(transactions, data, entity_id, currency):
    """Build a markdown table from transaction data."""
    if not transactions:
        return '*No transactions recorded yet.*'
    header = f'| Transaction | Counterparty | Amount ({currency}) |\n|---|---|---:|'
    rows = [header]
    for tx in transactions:
        name = tx.get('name', 'Unknown')
        from_id = tx.get('from_entity', '')
        to_id = tx.get('to_entity', '')
        counterparty_id = to_id if from_id == entity_id else from_id
        counterparty = counterparty_id
        for e in data.get('entities', []):
            if e.get('id') == counterparty_id:
                counterparty = e.get('name', counterparty_id)
                break
        amount = format_amount(tx.get('amount', 0))
        rows.append(f'| {name} | {counterparty} | {amount} |')
    return '\n'.join(rows)


def make_section_badge_md(content):
    """Return a markdown status indicator."""
    if content and not content.startswith('[No ') and not content.startswith('[UNRESOLVED'):
        return '`Complete`'
    return '`Pending`'


def make_section_body_md(content):
    """Return section body for markdown."""
    if content and not content.startswith('[No ') and not content.startswith('[UNRESOLVED'):
        return content
    return '*Awaiting input...*'


def populate_md_template(template_content, data, blueprint, entity, transactions, resolved_sections):
    """Replace all placeholders in the markdown template with actual values."""
    result = template_content

    # Entity fields
    entity_name = entity.get('name', 'Unknown Entity')
    entity_id = entity.get('id', '')
    result = result.replace('<<ENTITY_NAME>>', entity_name)

    # Group name
    group = data.get('group', {})
    group_name = group.get('name', 'Unknown Group') if isinstance(group, dict) else str(group)
    result = result.replace('<<GROUP_NAME>>', group_name)

    # Country
    result = result.replace('<<COUNTRY>>', entity.get('jurisdiction', entity.get('country', '—')))

    # Fiscal year (blueprint → local_file → entity fallback)
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', 'N/A'))
    result = result.replace('<<FISCAL_YEAR>>', str(fiscal_year))

    # Currency
    currency = 'EUR'
    if transactions:
        currency = transactions[0].get('currency', 'EUR')

    # Status
    sections = resolved_sections
    all_filled = all(
        v and not str(v).startswith('[No ') and not str(v).startswith('[UNRESOLVED')
        for v in sections.values()
    ) and len(transactions) > 0
    result = result.replace('<<STATUS>>', '`Ready`' if all_filled else '`In Progress`')

    # Section: Group Overview
    group_overview = resolved_sections.get('group_overview', '')
    result = result.replace('<<GROUP_OVERVIEW_BADGE>>', make_section_badge_md(group_overview))
    result = result.replace('<<GROUP_OVERVIEW_CONTENT>>', make_section_body_md(group_overview))

    # Section: Entity Introduction
    entity_intro = resolved_sections.get('entity_introduction', '')
    result = result.replace('<<ENTITY_INTRODUCTION_BADGE>>', make_section_badge_md(entity_intro))
    result = result.replace('<<ENTITY_INTRODUCTION_CONTENT>>', make_section_body_md(entity_intro))

    # Transactions
    tx_badge = make_section_badge_md('has_data' if transactions else '')
    result = result.replace('<<TRANSACTIONS_BADGE>>', tx_badge)
    result = result.replace('<<TRANSACTION_ROWS>>', build_transaction_rows_md(transactions, data, entity_id, currency))

    return result


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def escape_html(text):
    """Escape special HTML characters in text."""
    if not isinstance(text, str):
        return str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def build_transaction_rows_html(transactions, data, entity_id):
    """Build HTML table rows with editable input fields from transaction data."""
    if not transactions:
        return ''
    rows = []
    for tx in transactions:
        name = escape_html(tx.get('name', ''))
        from_id = tx.get('from_entity', '')
        to_id = tx.get('to_entity', '')
        counterparty_id = to_id if from_id == entity_id else from_id
        counterparty = counterparty_id
        for e in data.get('entities', []):
            if e.get('id') == counterparty_id:
                counterparty = escape_html(e.get('name', counterparty_id))
                break
        amount = format_amount(tx.get('amount', 0))
        tp_method = escape_html(tx.get('tp_method', '—'))
        tested_party = tx.get('tested_party', '')
        tested_profile = ''
        if tested_party == from_id:
            tested_profile = escape_html(tx.get('from_entity_profile', '—'))
        elif tested_party == to_id:
            tested_profile = escape_html(tx.get('to_entity_profile', '—'))
        rows.append(
            f'        <tr>\n'
            f'          <td><input class="cell-input" type="text" data-field="name" value="{name}"></td>\n'
            f'          <td><input class="cell-input" type="text" data-field="counterparty" value="{counterparty}"></td>\n'
            f'          <td><input class="cell-input" type="text" data-field="amount" value="{amount}"></td>\n'
            f'          <td>{tp_method.upper()}</td>\n'
            f'          <td>{tested_profile}</td>\n'
            f'        </tr>'
        )
    return '\n'.join(rows)


def build_notes_html(notes, context_label=""):
    """Build an HTML block for displaying notes on an object.

    Args:
        notes: list of note strings (or None/empty)
        context_label: optional label like "Entity" or "Transaction"

    Returns HTML string, or empty string if no notes.
    """
    if not notes:
        return ''
    items = ''.join(
        f'<li>{escape_html(note)}</li>' for note in notes
    )
    label = f' — {escape_html(context_label)}' if context_label else ''
    return (
        f'<div class="notes-block">'
        f'<div class="notes-header">Notes{label}</div>'
        f'<ul class="notes-list">{items}</ul>'
        f'</div>'
    )


def build_all_notes_html(data, entity, transactions, blueprint):
    """Build a combined notes HTML block for the intake preview.

    Gathers notes from group, entity, transactions, and blueprint section_notes.
    Returns HTML string (may be empty if no notes exist anywhere).
    """
    blocks = []

    # Group notes
    group = data.get('group', {})
    if isinstance(group, dict):
        group_notes = group.get('notes', [])
        if group_notes:
            blocks.append(build_notes_html(group_notes, group.get('name', 'Group')))

    # Entity notes
    entity_notes = entity.get('notes', [])
    if entity_notes:
        blocks.append(build_notes_html(entity_notes, entity.get('name', 'Entity')))

    # Transaction notes
    for tx in transactions:
        tx_notes = tx.get('notes', [])
        if tx_notes:
            blocks.append(build_notes_html(tx_notes, tx.get('name', 'Transaction')))

    # Blueprint section notes
    section_notes = blueprint.get('section_notes', {})
    if section_notes:
        note_items = [f"{key.replace('_', ' ').title()}: {val}" for key, val in section_notes.items() if val]
        if note_items:
            blocks.append(build_notes_html(note_items, "Report sections"))

    if not blocks:
        return ''

    return (
        '<div class="notes-container">'
        '<h3 class="notes-title">Notes from previous sessions</h3>'
        + ''.join(blocks) +
        '</div>'
    )


def make_section_badge(content):
    """Return a status badge based on whether section content exists."""
    if content and not content.startswith('[No ') and not content.startswith('[UNRESOLVED'):
        return '<span class="badge badge-success">Complete</span>'
    return '<span class="badge badge-warning">Pending</span>'


def get_section_text(content):
    """Return raw section text for a textarea, or empty string if placeholder."""
    if content and not content.startswith('[No ') and not content.startswith('[UNRESOLVED'):
        return escape_html(content)
    return ''


def build_editor_content_sections(resolved_sections, section_meta, blueprint,
                                   data=None, entity_id=None, transactions=None):
    """Build dynamic HTML blocks for all blueprint content sections, organized by category.

    Each section gets an editable textarea with a layer dot and status badge.
    Auto sections get read-only table rendering instead of textareas.
    Returns HTML string to replace <<CONTENT_SECTIONS>>.
    """
    section_notes = blueprint.get('section_notes', {})

    # Group by category
    categories = OrderedDict()
    for key in resolved_sections:
        cat_id, cat_label = categorize_section(key)
        if cat_id not in categories:
            categories[cat_id] = {'label': cat_label, 'keys': []}
        categories[cat_id]['keys'].append(key)

    # Order categories
    ordered = OrderedDict()
    for cat_id in CATEGORY_ORDER:
        if cat_id in categories:
            ordered[cat_id] = categories[cat_id]
    for cat_id in categories:
        if cat_id not in ordered:
            ordered[cat_id] = categories[cat_id]

    parts = []
    for cat_id, cat_info in ordered.items():
        parts.append(f'<div class="category-divider">{escape_html(cat_info["label"])}</div>')

        for key in cat_info['keys']:
            meta = section_meta.get(key, {})
            text = resolved_sections.get(key, '')
            label = humanize_section_key(key)
            complete = is_section_complete(text)
            badge = make_section_badge(text if complete else '')
            note = section_notes.get(key, '')

            # Layer indicator
            color = meta.get('color', '')
            layer_label = meta.get('label', '')
            layer_html = ''
            if color:
                layer_html = (
                    f'<span style="display:flex;align-items:center;gap:4px">'
                    f'<span class="layer-dot" style="background:{color}"></span>'
                    f'<span class="layer-label">{escape_html(layer_label)}</span>'
                    f'</span>'
                )

            # Note line
            note_html = ''
            if note:
                note_html = (
                    f'<div style="font-size:11px;color:var(--sn-primary);font-style:italic;'
                    f'margin-top:6px">{escape_html(note)}</div>'
                )

            # Auto sections: render as read-only table
            if is_auto_section(key) and data is not None and entity_id and transactions is not None:
                auto_html = build_auto_table_html(key, data, entity_id, transactions, blueprint)
                badge = '<span class="badge badge-auto">Auto</span>' if auto_html else badge
                content_block = (
                    f'    <div class="auto-table-container">{auto_html}</div>\n'
                    if auto_html else
                    f'    <div style="padding:12px;color:var(--sn-text-dim);font-style:italic">No data available</div>\n'
                )
            else:
                # Content section: editable textarea
                display_text = escape_html(text) if complete else ''
                placeholder = f'Write or ask Claude to draft: {label}'
                content_block = (
                    f'    <textarea class="edit-area" id="{escape_html(key)}" '
                    f'data-label="{escape_html(label)}" '
                    f'placeholder="{escape_html(placeholder)}">{display_text}</textarea>\n'
                )

            parts.append(
                f'<div class="section">\n'
                f'  <div class="section-header">\n'
                f'    <span class="section-label">{escape_html(label)}</span>\n'
                f'    <div style="display:flex;align-items:center;gap:10px">{layer_html}{badge}</div>\n'
                f'  </div>\n'
                f'  <div class="section-content">\n'
                f'{content_block}'
                f'{note_html}'
                f'  </div>\n'
                f'</div>'
            )

    return '\n'.join(parts)


def populate_html_template(template_content, data, blueprint, entity, transactions,
                           resolved_sections, section_meta=None):
    """Replace all placeholders in the interactive HTML editor template.

    Now dynamically renders all blueprint sections by category with layer info.
    """
    result = template_content

    # Entity fields
    entity_name = entity.get('name', 'Unknown Entity')
    entity_id = entity.get('id', '')
    result = result.replace('<<ENTITY_NAME>>', escape_html(entity_name))
    result = result.replace('<<ENTITY_ID>>', escape_html(entity_id))

    # Group name
    group = data.get('group', {})
    group_name = group.get('name', 'Unknown Group') if isinstance(group, dict) else str(group)
    result = result.replace('<<GROUP_NAME>>', escape_html(group_name))

    # Country / jurisdiction
    result = result.replace('<<COUNTRY>>', escape_html(entity.get('jurisdiction', entity.get('country', '—'))))

    # Fiscal year
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', 'N/A'))
    result = result.replace('<<FISCAL_YEAR>>', str(fiscal_year))

    # Currency
    currency = 'EUR'
    if transactions:
        currency = transactions[0].get('currency', 'EUR')
    result = result.replace('<<CURRENCY>>', currency)

    # Status badge
    all_filled = all(
        is_section_complete(v) for v in resolved_sections.values()
    ) and len(transactions) > 0
    status = 'Ready' if all_filled else 'In Progress'
    result = result.replace('<<STATUS>>', status)

    # Dynamic content sections by category
    if section_meta is None:
        section_meta = {}
    content_html = build_editor_content_sections(resolved_sections, section_meta, blueprint,
                                                    data=data, entity_id=entity_id, transactions=transactions)
    result = result.replace('<<CONTENT_SECTIONS>>', content_html)

    # Transactions badge + editable rows
    tx_badge = make_section_badge('has_data' if transactions else '')
    result = result.replace('<<TRANSACTIONS_BADGE>>', tx_badge)
    result = result.replace('<<TRANSACTION_ROWS>>', build_transaction_rows_html(transactions, data, entity_id))

    # Notes block
    notes_html = build_all_notes_html(data, entity, transactions, blueprint)
    result = result.replace('<<NOTES_BLOCK>>', notes_html)

    return result


# ---------------------------------------------------------------------------
# Report view helpers (non-editable document with X-ray annotations)
# ---------------------------------------------------------------------------

def build_transaction_rows_report(transactions, data, entity_id, currency):
    """Build static HTML table rows for the report view (non-editable)."""
    if not transactions:
        return '<tr><td colspan="4" style="color:var(--text-dim);font-style:italic">No controlled transactions recorded</td></tr>'
    rows = []
    for tx in transactions:
        name = escape_html(tx.get('name', 'Unknown'))
        from_id = tx.get('from_entity', '')
        to_id = tx.get('to_entity', '')
        counterparty_id = to_id if from_id == entity_id else from_id
        counterparty = counterparty_id
        for e in data.get('entities', []):
            if e.get('id') == counterparty_id:
                counterparty = escape_html(e.get('name', counterparty_id))
                break
        amount = format_amount(tx.get('amount', 0))
        tp_method = escape_html(tx.get('tp_method', '—')).upper()
        tested_party = tx.get('tested_party', '')
        tested_profile = ''
        if tested_party == from_id:
            tested_profile = escape_html(tx.get('from_entity_profile', '—'))
        elif tested_party == to_id:
            tested_profile = escape_html(tx.get('to_entity_profile', '—'))
        rows.append(
            f'        <tr>\n'
            f'          <td>{name} ({counterparty})</td>\n'
            f'          <td>{amount}</td>\n'
            f'          <td>{tp_method}</td>\n'
            f'          <td>{tested_profile}</td>\n'
            f'        </tr>'
        )
    return '\n'.join(rows)


def make_source_line_html(meta):
    """Build the source-path annotation line if a @reference or @library path exists.

    For composite sections, shows each part's source on its own line.
    """
    if meta.get('composite') and meta.get('parts'):
        lines = []
        for i, part in enumerate(meta['parts'], 1):
            path = part.get('source_path')
            if path:
                lines.append(f'<div class="annotation-source">Part {i}: <code>{escape_html(path)}</code></div>')
        return '\n'.join(lines)
    path = meta.get('source_path')
    if path:
        return f'<div class="annotation-source">Source: <code>{escape_html(path)}</code></div>'
    return ''


def make_composite_label_html(meta):
    """Build a composite badge showing which layers contribute to this section.

    Returns empty string for non-composite sections.
    """
    if not meta.get('composite'):
        return ''
    labels = meta.get('composite_labels', [])
    if len(labels) <= 1:
        return ''
    dots = []
    for part in meta.get('parts', []):
        dots.append(
            f'<span class="annotation-dot" style="background:{part["color"]}"></span>'
            f'<span style="color:{part["color"]};font-size:10px">{part["label"]}</span>'
        )
    return (
        '<div class="annotation-bar" style="margin-top:4px;padding:4px 10px;font-size:10px">'
        '<span style="color:var(--sn-text-dim);margin-right:4px">Composite:</span>'
        + ' <span style="color:var(--sn-text-dim)">+</span> '.join(dots)
        + '</div>'
    )


def make_section_note_html(note):
    """Build an annotation line for a blueprint section note.

    Shown in X-ray mode alongside layer/impact/source annotations.
    Returns empty string if no note exists.
    """
    if not note:
        return ''
    return f'<div class="annotation-note">Note: {escape_html(note)}</div>'


def build_xray_annotation_html(meta, note=''):
    """Build the X-ray annotation block for a single section.

    Returns HTML string with the annotation bar, source path, composite badge,
    and section note — all hidden by default, shown when X-ray mode is toggled.
    """
    color = meta.get('color', '#3b82f6')
    label = escape_html(meta.get('label', 'Entity'))
    impact = escape_html(meta.get('impact', ''))

    source_line = make_source_line_html(meta)
    composite_line = make_composite_label_html(meta)
    note_line = make_section_note_html(note)

    return (
        '<div class="annotation">'
        '<div class="annotation-bar">'
        f'<span class="annotation-dot" style="background:{color}"></span>'
        f'<span class="annotation-label" style="color:{color}">{label}</span>'
        '<span style="color:var(--sn-text-dim)">&middot;</span>'
        f'<span class="annotation-impact">{impact}</span>'
        '</div>'
        f'{source_line}{composite_line}{note_line}'
        '</div>'
    )


def populate_report_template(template_content, data, blueprint, entity, transactions,
                             resolved_sections, section_meta):
    """Replace all placeholders in the report view HTML template.

    Dynamically generates all sections from the blueprint with X-ray annotations.
    Sections are organized by category with headers and hierarchical numbering.
    A controlled transactions summary table is injected automatically.
    """
    result = template_content

    # --- Basic entity info ---
    entity_name = entity.get('name', 'Unknown Entity')
    entity_id = entity.get('id', '')
    result = result.replace('<<ENTITY_NAME>>', escape_html(entity_name))
    result = result.replace('<<ENTITY_ID>>', escape_html(entity_id))

    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', 'N/A'))
    result = result.replace('<<FISCAL_YEAR>>', str(fiscal_year))

    currency = 'EUR'
    if transactions:
        currency = transactions[0].get('currency', 'EUR')
    result = result.replace('<<CURRENCY>>', currency)

    # --- Organize sections by category ---
    section_notes = blueprint.get('section_notes', {})
    categories = OrderedDict()

    for key in resolved_sections:
        cat_id, cat_label = categorize_section(key)
        if cat_id not in categories:
            categories[cat_id] = {'label': cat_label, 'keys': []}
        categories[cat_id]['keys'].append(key)

    # Re-order categories
    ordered = OrderedDict()
    for cat_id in CATEGORY_ORDER:
        if cat_id in categories:
            ordered[cat_id] = categories[cat_id]
    for cat_id in categories:
        if cat_id not in ordered:
            ordered[cat_id] = categories[cat_id]

    # --- Build sections HTML ---
    parts = []
    cat_num = 0

    for cat_id, cat_info in ordered.items():
        cat_num += 1
        parts.append(f'  <div class="doc-category">{escape_html(cat_info["label"])}</div>')

        sub_num = 0
        for key in cat_info['keys']:
            sub_num += 1
            meta = section_meta.get(key, classify_source('', key))
            text = resolved_sections.get(key, '')
            note = section_notes.get(key, '')
            label = humanize_section_key(key)
            layer = meta.get('layer', 4)

            annotation = build_xray_annotation_html(meta, note)

            if is_auto_section(key):
                auto_html = build_auto_table_html(key, data, entity_id, transactions, blueprint)
                body_html = f'<div class="doc-body">{auto_html}</div>' if auto_html else '<div class="doc-body-pending">[Auto — no data]</div>'
            elif is_section_complete(text):
                body_html = f'<div class="doc-body">{escape_html(text)}</div>'
            else:
                body_html = '<div class="doc-body-pending">[Pending]</div>'

            parts.append(
                f'  <div class="annotated-section" data-layer="{layer}">\n'
                f'    {annotation}\n'
                f'    <div class="doc-section-title">{cat_num}.{sub_num} {escape_html(label)}</div>\n'
                f'    {body_html}\n'
                f'  </div>'
            )

        # After business description category, insert the transactions summary table
        if cat_id == 'business' and transactions:
            cat_num += 1
            tx_rows = build_transaction_rows_report(transactions, data, entity_id, currency)
            parts.append(
                f'  <div class="doc-category">Controlled Transactions Overview</div>\n'
                f'  <div class="annotated-section" data-layer="4">\n'
                f'    <div class="annotation">\n'
                f'      <div class="annotation-bar">\n'
                f'        <span class="annotation-dot" style="background:var(--sn-layer4)"></span>\n'
                f'        <span class="annotation-label" style="color:var(--sn-layer4)">Auto</span>\n'
                f'        <span style="color:var(--sn-text-dim)">&middot;</span>\n'
                f'        <span class="annotation-impact">Generated from transaction data</span>\n'
                f'      </div>\n'
                f'    </div>\n'
                f'    <div class="doc-body">The following table summarises the controlled transactions '
                f'of {escape_html(entity_name)} for the fiscal year {fiscal_year}.</div>\n'
                f'    <table class="doc-table">\n'
                f'      <caption>Controlled Transactions Overview</caption>\n'
                f'      <thead><tr>'
                f'<th>Transaction</th><th>Amount ({currency})</th>'
                f'<th>Method</th><th>Tested party profile</th>'
                f'</tr></thead>\n'
                f'      <tbody>{tx_rows}</tbody>\n'
                f'    </table>\n'
                f'  </div>'
            )

    result = result.replace('<<REPORT_SECTIONS>>', '\n\n'.join(parts))
    return result


# ---------------------------------------------------------------------------
# Section-focused helpers (dashboard + section editor)
# ---------------------------------------------------------------------------

BUSINESS_KEYS = {'executive_summary', 'group_overview', 'entity_introduction'}

# Financial transaction types — different rendering (transposed contractual terms, no characteristics)
FINANCIAL_TYPES = {
    'loan-arrangement', 'cash-pooling', 'financial-guarantees',
    'factoring', 'hybrid-instruments', 'asset-management',
    'captive-insurance', 'cost-contribution-arrangement',
}


def humanize_transaction_type(tx_type):
    """Convert a transaction type slug to a human-readable label.

    'tangible-goods' -> 'Transfer of Tangible Goods'
    'loan-arrangement' -> 'Loan Arrangements'
    """
    type_map = {
        'tangible-goods': 'Transfer of Tangible Goods',
        'services': 'Provision of Services',
        'intangibles': 'Licensing of Intangibles',
        'sale-of-intangibles': 'Sale of Intangibles',
        'loan-arrangement': 'Loan Arrangements',
        'cash-pooling': 'Cash Pooling',
        'financial-guarantees': 'Financial Guarantees',
        'factoring': 'Receivables Factoring',
        'hybrid-instruments': 'Hybrid Instruments',
        'captive-insurance': 'Captive Insurance',
        'cost-contribution-arrangement': 'Cost Contribution Arrangements',
        'asset-management': 'Asset Management',
    }
    return type_map.get(tx_type, tx_type.replace('-', ' ').title())


def categorize_section(key):
    """Determine the category for a section based on its key naming convention.

    Returns (category_id, category_label) tuple.
    """
    if key.startswith('preamble_'):
        return ('preamble', 'Report Preamble')
    if key in BUSINESS_KEYS or key.startswith('management_') or key.startswith('business_') or key.startswith('local_') or key.startswith('intangible_'):
        return ('business', 'Business Description')
    if key.startswith('industry_analysis'):
        return ('industry', 'Industry Analysis')
    if key.startswith('fp_'):
        return ('functional', 'Functional Analysis')
    if key.startswith('tx_'):
        return ('transactions', 'Controlled Transactions')
    if key.startswith('bm_'):
        return ('benchmark', 'Benchmark Application')
    if key.startswith('transactions_not_covered') or key == 'appendices':
        return ('closing', 'Closing')
    return ('other', 'Other')


# Preferred display order for categories on the dashboard
CATEGORY_ORDER = [
    'preamble', 'business', 'industry', 'functional',
    'transactions', 'benchmark', 'closing', 'other'
]


def humanize_section_key(key):
    """Convert a blueprint section key to a human-readable label.

    Examples:
        group_overview → Group Overview
        fp_limited_risk_distributor_functions → Limited Risk Distributor Functions
        tx_001_summary → 001 Summary
        bm_benchmark_a_conclusion → Benchmark A Conclusion
    """
    display = key
    for prefix in ['preamble_', 'fp_', 'tx_', 'bm_']:
        if display.startswith(prefix):
            display = display[len(prefix):]
            break
    return display.replace('_', ' ').title()


def is_section_complete(text):
    """Check if a section has meaningful content (not a placeholder)."""
    return bool(text and not str(text).startswith('[No ') and not str(text).startswith('[UNRESOLVED'))


def populate_dashboard_template(template_content, data, blueprint, entity,
                                transactions, resolved_sections, section_meta):
    """Generate the section dashboard HTML showing all sections with status.

    Organizes blueprint sections by category (detected from key naming convention),
    adds auto-generated data sections, and shows completion progress.
    """
    result = template_content

    # --- Basic entity info ---
    entity_name = entity.get('name', 'Unknown Entity')
    result = result.replace('<<ENTITY_NAME>>', escape_html(entity_name))
    result = result.replace('<<ENTITY_ID>>', escape_html(entity.get('id', '')))
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', 'N/A'))
    result = result.replace('<<FISCAL_YEAR>>', str(fiscal_year))

    # --- Organize sections by category ---
    categories = OrderedDict()
    for cat_id in CATEGORY_ORDER:
        pass  # pre-seed order; only populated categories will be shown

    for key in resolved_sections:
        cat_id, cat_label = categorize_section(key)
        if cat_id not in categories:
            categories[cat_id] = {'label': cat_label, 'sections': []}
        text = resolved_sections[key]
        meta = section_meta.get(key, {})
        categories[cat_id]['sections'].append({
            'key': key,
            'label': humanize_section_key(key),
            'complete': is_section_complete(text),
            'is_auto': False,
            'layer_color': meta.get('color', ''),
            'layer_label': meta.get('label', ''),
        })

    # --- Add transactions as an auto-data card ---
    tx_cat = categories.get('transactions')
    if not tx_cat:
        categories['transactions'] = {'label': 'Controlled Transactions', 'sections': []}
        tx_cat = categories['transactions']
    tx_cat['sections'].insert(0, {
        'key': '_auto_transactions_table',
        'label': f'Transactions Data ({len(transactions)} recorded)',
        'complete': len(transactions) > 0,
        'is_auto': True,
        'layer_color': '',
        'layer_label': '',
    })

    # --- Re-order categories ---
    ordered = OrderedDict()
    for cat_id in CATEGORY_ORDER:
        if cat_id in categories:
            ordered[cat_id] = categories[cat_id]
    for cat_id in categories:
        if cat_id not in ordered:
            ordered[cat_id] = categories[cat_id]

    # --- Progress stats ---
    all_sections = [s for c in ordered.values() for s in c['sections']]
    total = len(all_sections)
    complete = sum(1 for s in all_sections if s['complete'])
    pct = round(complete / total * 100) if total > 0 else 0

    result = result.replace('<<PROGRESS_FRACTION>>', f'{complete} of {total} sections')
    result = result.replace('<<PROGRESS_DETAIL>>', f'{pct}% complete')
    result = result.replace('<<PROGRESS_PCT>>', str(pct))

    # --- Build section cards HTML ---
    cards_html = []
    for cat_id, cat_info in ordered.items():
        if not cat_info['sections']:
            continue
        cards_html.append('<div class="category">')
        cards_html.append(f'  <div class="category-header">{escape_html(cat_info["label"])}</div>')
        cards_html.append('  <div class="category-cards">')
        for sec in cat_info['sections']:
            if sec.get('is_auto'):
                status_class, badge_class, badge_text = 'status-auto', 'badge-auto', 'Auto'
            elif sec['complete']:
                status_class, badge_class, badge_text = 'status-complete', 'badge-complete', 'Complete'
            else:
                status_class, badge_class, badge_text = 'status-pending', 'badge-pending', 'Pending'

            layer_dot = ''
            if sec.get('layer_color'):
                layer_dot = f'<span class="layer-dot" style="background:{sec["layer_color"]}"></span>'

            cards_html.append(
                f'    <div class="section-card" data-key="{escape_html(sec["key"])}">'
                f'<span class="section-status {status_class}"></span>'
                f'<div class="section-info"><div class="section-label">{escape_html(sec["label"])}</div></div>'
                f'<div class="section-meta">{layer_dot}'
                f'<span class="badge {badge_class}">{badge_text}</span></div>'
                f'</div>'
            )
        cards_html.append('  </div>')
        cards_html.append('</div>')

    result = result.replace('<<SECTION_CARDS>>', '\n'.join(cards_html))
    return result


def populate_section_editor(template_content, data, blueprint, entity,
                            transactions, resolved_sections, section_meta, section_key):
    """Generate the single-section editor HTML for one blueprint section.

    Renders either an editable textarea (content sections) or a read-only
    data display (auto-generated sections).
    """
    result = template_content

    # --- Basic entity info ---
    entity_name = entity.get('name', 'Unknown Entity')
    result = result.replace('<<ENTITY_NAME>>', escape_html(entity_name))
    result = result.replace('<<ENTITY_ID>>', escape_html(entity.get('id', '')))
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', 'N/A'))
    result = result.replace('<<FISCAL_YEAR>>', str(fiscal_year))
    result = result.replace('<<SECTION_KEY>>', escape_html(section_key))

    # --- Section category and label ---
    cat_id, cat_label = categorize_section(section_key)
    result = result.replace('<<SECTION_CATEGORY>>', escape_html(cat_label))
    section_label = humanize_section_key(section_key)
    result = result.replace('<<SECTION_LABEL>>', escape_html(section_label))

    # --- Layer badge ---
    meta = section_meta.get(section_key, {})
    if meta.get('color'):
        badge_html = (
            f'<span class="layer-badge" style="border-color: {meta["color"]}30; background: {meta["color"]}10;">'
            f'<span class="dot" style="background: {meta["color"]}"></span>'
            f'{escape_html(meta.get("label", ""))}'
            f'</span>'
        )
    else:
        badge_html = ''
    result = result.replace('<<LAYER_BADGE>>', badge_html)

    # --- Source path ---
    source_path = meta.get('source_path', '')
    if source_path:
        result = result.replace('<<SOURCE_PATH>>',
                                f'<span class="source-path">{escape_html(source_path)}</span>')
    else:
        result = result.replace('<<SOURCE_PATH>>', '')

    # --- Section note ---
    section_notes = blueprint.get('section_notes', {})
    note = section_notes.get(section_key, '')
    if note:
        result = result.replace('<<SECTION_NOTE>>',
                                f'<div class="section-note">Note: {escape_html(note)}</div>')
    else:
        result = result.replace('<<SECTION_NOTE>>', '')

    # --- Content area ---
    text = resolved_sections.get(section_key, '')
    is_auto = section_key.startswith('_auto_')

    if is_auto:
        content_html = (
            '<span class="auto-label">Auto-generated from your data</span>'
            '<div class="auto-table-container">'
            '<p style="padding:16px;color:var(--sn-text-muted);">'
            'This section is built automatically from your records.</p></div>'
        )
        result = result.replace('<<SECTION_CONTENT>>', content_html)
        result = result.replace('<<ACTION_BAR>>', '')
    else:
        display_text = get_section_text(text) if text else ''
        content_html = (
            f'<textarea class="edit-area" data-original="{escape_html(display_text)}"'
            f' placeholder="Enter content for this section...">'
            f'{display_text}</textarea>'
        )
        action_bar = (
            '<div class="action-bar">'
            '<button class="btn btn-primary" onclick="sendUpdates()">Send updates</button>'
            '<span class="copy-status"></span>'
            '</div>'
        )
        result = result.replace('<<SECTION_CONTENT>>', content_html)
        result = result.replace('<<ACTION_BAR>>', action_bar)

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_inputs(data, blueprint, entity):
    """Check that all required data is present. Print warnings for missing fields."""
    warnings = []

    if not entity.get('name'):
        warnings.append("Entity has no 'name' — output filename will be generic")
    if not blueprint.get('fiscal_year') and not entity.get('fiscal_year'):
        warnings.append("No fiscal_year found on blueprint or entity")

    sections = blueprint.get('sections', {})
    if not sections.get('group_overview'):
        warnings.append("Blueprint has no 'group_overview' section — will show placeholder")
    if not sections.get('entity_introduction'):
        warnings.append("Blueprint has no 'entity_introduction' section — will show placeholder")

    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    return len(warnings) == 0


# ---------------------------------------------------------------------------
# Template population
# ---------------------------------------------------------------------------

def populate_latex_template(template_content, data, blueprint, entity, transactions, resolved_sections):
    """Replace all placeholders in the LaTeX template with actual values.

    Uses build_report_body_latex() to generate the full <<REPORT_BODY>> content
    dynamically from blueprint sections and auto-generated tables.
    """
    result = template_content

    # Entity fields
    result = result.replace('<<ENTITY_NAME>>', escape_latex(entity.get('name', 'Unknown Entity')))

    # Fiscal year: blueprint is the authority, fall back to entity
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', 'N/A'))
    result = result.replace('<<FISCAL_YEAR>>', str(fiscal_year))

    # Build the full report body
    report_body = build_report_body_latex(blueprint, resolved_sections, data, entity, transactions)
    result = result.replace('<<REPORT_BODY>>', report_body)

    return result


# ---------------------------------------------------------------------------
# PDF compilation
# ---------------------------------------------------------------------------

def compile_pdf(tex_path, output_dir):
    """Compile a .tex file to PDF using pdflatex.

    Runs pdflatex twice to ensure the table of contents and cross-references
    are fully resolved.
    """
    try:
        for pass_num in range(1, 3):
            print(f"  pdflatex pass {pass_num}/2...")
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', output_dir, tex_path],
                capture_output=True
            )
            if result.returncode != 0:
                log_text = result.stdout.decode('utf-8', errors='replace')
                print(f"Error compiling PDF. LaTeX log:\n{log_text}", file=sys.stderr)
                sys.exit(1)
        print("PDF compiled successfully")
    except FileNotFoundError:
        print("Error: pdflatex not found on PATH.", file=sys.stderr)
        print("  If on macOS: brew install --cask basictex && eval \"$(/usr/libexec/path_helper)\"", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Combined (Workspace Editor) helpers
# ---------------------------------------------------------------------------

def build_progress_metrics(blueprint, local_file):
    """Calculate progress metrics from blueprint sections and local_file status."""
    sections = blueprint.get('sections', {})
    total = len(sections)
    status_map = local_file.get('section_status', {}) if local_file else {}
    reviewed = sum(1 for s in status_map.values() if s.get('reviewed'))
    signoff = sum(1 for s in status_map.values() if s.get('signed_off'))
    review_pct = round(reviewed / total * 100) if total else 0
    signoff_pct = round(signoff / total * 100) if total else 0
    return {
        'total': total,
        'reviewed': reviewed,
        'signoff': signoff,
        'review_pct': review_pct,
        'signoff_pct': signoff_pct,
    }


def build_jurisdiction_svg(country, references_dir):
    """Build an SVG map element highlighting the given country."""
    maps_path = os.path.join(references_dir, 'jurisdiction-maps.json')
    if not os.path.exists(maps_path):
        return ''
    with open(maps_path, 'r') as f:
        maps_data = json.load(f)

    jurisdictions = maps_data.get('jurisdictions', {})
    if country not in jurisdictions:
        return ''

    entry = jurisdictions[country]
    view_box = entry.get('viewBox', '0 0 800 700')
    paths = entry.get('paths', [])

    parts = [f'<svg class="map-svg" viewBox="{escape_html(view_box)}" xmlns="http://www.w3.org/2000/svg">']
    for p in paths:
        role = p.get('role', 'context')
        css_class = 'map-highlight' if role == 'highlight' else 'map-land'
        parts.append(f'  <path class="{css_class}" d="{p["d"]}"/>')
    parts.append('</svg>')
    return '\n'.join(parts)


def build_general_notes_html(data, entity, transactions):
    """Build note-group divs for the general notes panel."""
    groups = []

    # Group notes
    group = data.get('group', {})
    if isinstance(group, dict) and group.get('notes'):
        items = ''.join(f'<li>{escape_html(n)}</li>' for n in group['notes'][:2])
        groups.append(
            f'<div class="note-group">'
            f'<div class="note-group-title" contenteditable="true">{escape_html(group.get("name", "Group"))}</div>'
            f'<ul class="note-list" contenteditable="true">{items}</ul>'
            f'</div>'
        )

    # Entity notes
    if entity.get('notes'):
        items = ''.join(f'<li>{escape_html(n)}</li>' for n in entity['notes'][:2])
        groups.append(
            f'<div class="note-group">'
            f'<div class="note-group-title" contenteditable="true">{escape_html(entity.get("name", "Entity"))}</div>'
            f'<ul class="note-list" contenteditable="true">{items}</ul>'
            f'</div>'
        )

    # Transaction notes
    for tx in transactions:
        if tx.get('notes'):
            items = ''.join(f'<li>{escape_html(n)}</li>' for n in tx['notes'][:2])
            groups.append(
                f'<div class="note-group">'
                f'<div class="note-group-title" contenteditable="true">{escape_html(tx.get("name", "Transaction"))}</div>'
                f'<ul class="note-list" contenteditable="true">{items}</ul>'
                f'</div>'
            )

    return '\n'.join(groups)


def build_blueprint_modal_html(blueprints_dir, current_blueprint):
    """Build blueprint cards for the modal from all blueprint files in directory."""
    cards = []
    current_name = current_blueprint.get('name', '')
    current_entity = current_blueprint.get('entity', '')

    if blueprints_dir and os.path.isdir(blueprints_dir):
        for fname in sorted(os.listdir(blueprints_dir)):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(blueprints_dir, fname)
            try:
                with open(fpath, 'r') as f:
                    bp = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            bp_name = escape_html(bp.get('name', 'OECD Blueprint'))
            bp_entity = bp.get('entity', '')
            bp_fy = bp.get('fiscal_year', '')
            bp_type = bp.get('type', 'local-file')
            section_count = len(bp.get('sections', {}))
            is_active = (bp_name == escape_html(current_name) and bp_entity == current_entity)
            active_cls = ' active' if is_active else ''
            badge_cls = 'builtin' if bp.get('blueprint_type') == 'builtin' else 'custom'
            badge_label = 'Standard' if bp.get('blueprint_type') == 'builtin' else 'Custom'

            # Build miniature preview from chapters
            preview_parts = []
            for ch in bp.get('chapters', []):
                preview_parts.append(f'<div class="bp-preview-chapter">{escape_html(ch.get("title", ""))}</div>')
                for _ in ch.get('sections', []):
                    preview_parts.append('<div class="bp-preview-section l4" style="width:80%"></div>')

            cards.append(
                f'<div class="bp-card{active_cls}">'
                f'<div class="bp-card-preview">{"".join(preview_parts)}</div>'
                f'<div class="bp-card-info">'
                f'<span class="bp-card-badge {badge_cls}">{badge_label}</span>'
                f'<div class="bp-card-name">{bp_name}</div>'
                f'<div class="bp-card-meta">{escape_html(bp_type.replace("-", " ").title())} &middot; {section_count} sections</div>'
                f'</div></div>'
            )

    # "New Blueprint" card — hidden for now (only one template available)
    # Will re-enable when additional blueprint templates are introduced

    return '\n'.join(cards)


def build_combined_element_html(key, text, meta, note, footnotes, status,
                                chapter_num, sub_num, data, entity_id,
                                transactions, blueprint, show_subheading=True):
    """Generate HTML for one content element in the Workspace Editor view."""
    parts = []
    slug = slugify(key)
    reviewed = 'true' if status.get('reviewed') else 'false'
    signed_off = 'true' if status.get('signed_off') else 'false'
    layer = meta.get('layer', 4)
    layer_cls = f'xray-layer{layer}'
    label = humanize_section_key(key)
    is_auto = is_auto_section(key)

    # Subheading (suppressed when parent section/subsection heading already provides structure)
    if show_subheading:
        parts.append(
            f'<div class="section-subheading" id="{slug}" '
            f'data-section-key="{escape_html(key)}" '
            f'data-reviewed="{reviewed}" data-signed-off="{signed_off}">'
            f'{chapter_num}.{sub_num} {escape_html(label)}'
            f'<span class="edit-pen"><svg><use href="#icon-pencil"/></svg></span>'
            f'</div>'
        )

    # Insert divider
    parts.append(
        '<div class="insert-divider">'
        '<div class="insert-divider-hit" onclick="insertElement(this.parentNode.querySelector(\'.insert-divider-btn\'))"></div>'
        '<button class="insert-divider-btn" onclick="insertElement(this)" title="Add element here"><svg><use href="#icon-chat"/></svg></button>'
        '<div class="insert-divider-line"></div>'
        '</div>'
    )

    # Content body
    if is_auto:
        auto_html = build_auto_table_html(key, data, entity_id, transactions, blueprint)
        parts.append(
            f'<div class="section-body-wrapper">'
            f'<div class="section-body {layer_cls} collapsed" contenteditable="false" '
            f'data-section-key="{escape_html(key)}">'
            f'{auto_html}'
            f'<button class="expand-btn" onclick="toggleExpand(this)"><span class="expand-icon">&#9662;</span></button>'
            f'</div>'
            f'</div>'
        )
    else:
        escaped_text = escape_html(text) if text else ''
        # data-original stores the original text for dirty tracking
        attr_original = escape_html(text).replace('"', '&quot;') if text else ''
        parts.append(
            f'<div class="section-body-wrapper">'
            f'<div class="section-body {layer_cls} collapsed" contenteditable="true" '
            f'data-section-key="{escape_html(key)}" data-original="{attr_original}">'
            f'<button class="chat-btn" title="AI edit" onclick="chatEdit(this)"><svg><use href="#icon-chat"/></svg></button>'
            f'{escaped_text}'
            f'<button class="expand-btn" onclick="toggleExpand(this)"><span class="expand-icon">&#9662;</span></button>'
            f'</div>'
        )

        # Element note
        note_items = ''
        if isinstance(note, list):
            note_items = ''.join(f'<li>{escape_html(n)}</li>' for n in note)
        elif isinstance(note, str) and note:
            note_items = f'<li>{escape_html(note)}</li>'
        parts.append(
            f'<div class="element-note">'
            f'<div class="element-note-header">'
            f'<div class="element-note-label">{escape_html(label)} notes</div>'
            f'<button class="note-chat-btn" title="AI edit notes" onclick="chatEditNote(this)"><svg><use href="#icon-chat"/></svg></button>'
            f'</div>'
            f'<ul class="note-list" contenteditable="true">{note_items}</ul>'
            f'</div>'
        )

        # Footnotes
        if footnotes:
            fn_entries = ''
            for i, ft in enumerate(footnotes, 1):
                fn_entries += (
                    f'<div class="footnote-entry">'
                    f'<span class="footnote-num">{i}</span>'
                    f'<span class="footnote-text">{escape_html(ft)}</span>'
                    f'</div>'
                )
            parts.append(f'<div class="element-footnote">{fn_entries}</div>')

        parts.append('</div>')  # close section-body-wrapper

    return '\n'.join(parts)


def build_combined_sections_html(blueprint, resolved_sections, section_meta,
                                 data, entity_id, transactions):
    """Build all document sections HTML from blueprint chapters (3-level)."""
    parts = []
    local_file = None
    for lf in data.get('local_files', []):
        if lf.get('entity') == entity_id:
            local_file = lf
            break

    section_notes = blueprint.get('section_notes', {})
    section_status = local_file.get('section_status', {}) if local_file else {}
    footnotes_all = blueprint.get('footnotes', {})

    for chapter_num, chapter in enumerate(blueprint.get('chapters', []), 1):
        chapter_id = chapter.get('id', slugify(chapter.get('title', f'chapter-{chapter_num}')))
        chapter_title = chapter.get('title', f'Chapter {chapter_num}')
        sections = chapter.get('sections', [])

        chapter_status = section_status.get(chapter_id, {})
        ch_reviewed = 'true' if chapter_status.get('reviewed') else 'false'
        ch_signed_off = 'true' if chapter_status.get('signed_off') else 'false'

        parts.append(f'<div class="section" id="{escape_html(chapter_id)}">')
        parts.append(
            f'  <div class="section-heading" data-section-key="{escape_html(chapter_id)}"'
            f' data-reviewed="{ch_reviewed}" data-signed-off="{ch_signed_off}">'
            f'{chapter_num} {escape_html(chapter_title)}'
            f'<span class="edit-pen"><svg><use href="#icon-pencil"/></svg></span></div>'
        )

        for sec_num, section in enumerate(sections, 1):
            # Handle legacy format (string key) for backward compat
            if isinstance(section, str):
                key = section
                meta = section_meta.get(key, classify_source('', key))
                text = resolved_sections.get(key, '')
                note = section_notes.get(key, '')
                fn = footnotes_all.get(key, [])
                status = section_status.get(key, {})
                parts.append(build_combined_element_html(
                    key, text, meta, note, fn, status,
                    chapter_num, sec_num, data, entity_id, transactions, blueprint
                ))
                continue

            # New format: section object with id, title, keys[], subsections[]
            sec_id = section.get('id', '')
            sec_title = section.get('title', '')
            sec_keys = section.get('keys', [])
            subsections = section.get('subsections', [])

            # Section heading (e.g., "2.1 Group Overview")
            section_slug = f'{chapter_id}-{sec_id}' if sec_id else f'{chapter_id}-sec-{sec_num}'
            parts.append(
                f'<div class="section-sec-heading" id="{escape_html(section_slug)}">'
                f'{chapter_num}.{sec_num} {escape_html(sec_title)}'
                f'<span class="edit-pen"><svg><use href="#icon-pencil"/></svg></span>'
                f'</div>'
            )

            # Render section-level content elements
            for key in sec_keys:
                meta = section_meta.get(key, classify_source('', key))
                text = resolved_sections.get(key, '')
                note = section_notes.get(key, '')
                fn = footnotes_all.get(key, [])
                status = section_status.get(key, {})
                parts.append(build_combined_element_html(
                    key, text, meta, note, fn, status,
                    chapter_num, sec_num, data, entity_id, transactions, blueprint,
                    show_subheading=False
                ))

            # Render subsections
            for subsec_num, subsec in enumerate(subsections, 1):
                subsec_id = subsec.get('id', '')
                subsec_title = subsec.get('title', '')
                subsec_keys = subsec.get('keys', [])
                subsec_slug = f'{chapter_id}-{sec_id}-{subsec_id}' if subsec_id else f'{chapter_id}-{sec_id}-sub-{subsec_num}'

                # Subsection heading (e.g., "2.1.1 Organizational Structure")
                parts.append(
                    f'<div class="section-subsec-heading" id="{escape_html(subsec_slug)}">'
                    f'{chapter_num}.{sec_num}.{subsec_num} {escape_html(subsec_title)}'
                    f'<span class="edit-pen"><svg><use href="#icon-pencil"/></svg></span>'
                    f'</div>'
                )

                for key in subsec_keys:
                    meta = section_meta.get(key, classify_source('', key))
                    text = resolved_sections.get(key, '')
                    note = section_notes.get(key, '')
                    fn = footnotes_all.get(key, [])
                    status = section_status.get(key, {})
                    parts.append(build_combined_element_html(
                        key, text, meta, note, fn, status,
                        chapter_num, sec_num, data, entity_id, transactions, blueprint,
                        show_subheading=False
                    ))

        parts.append('</div>')  # close section div

    return '\n'.join(parts)


def populate_combined_template(template_content, data, blueprint, entity,
                               transactions, resolved_sections, section_meta,
                               blueprints_dir, references_dir=None):
    """Replace all <<PLACEHOLDER>> markers in the Workspace Editor template."""
    result = template_content
    entity_id = entity.get('id', '')
    entity_name = entity.get('name', '')
    fiscal_year = str(blueprint.get('fiscal_year', entity.get('fiscal_year', '')))
    country = entity.get('jurisdiction', entity.get('country', ''))
    blueprint_name = blueprint.get('name', 'OECD Blueprint')

    # Find local_file object for this entity
    local_file = None
    for lf in data.get('local_files', []):
        if lf.get('entity') == entity_id:
            local_file = lf
            break

    # Group name
    group = data.get('group', {})
    group_name = group.get('name', '') if isinstance(group, dict) else ''

    # Document meta
    doc_title = 'Local File'
    doc_subtitle = entity_name
    doc_meta_parts = ['Transfer Pricing Documentation']
    if fiscal_year:
        doc_meta_parts.append(f'Fiscal Year {fiscal_year}')
    doc_meta = ' &middot; '.join(doc_meta_parts)
    if local_file:
        doc_title = local_file.get('title', doc_title)
        doc_subtitle = local_file.get('subtitle', doc_subtitle)
        if local_file.get('meta'):
            doc_meta = escape_html(local_file['meta'])

    # Simple string replacements
    result = result.replace('<<GROUP_NAME>>', escape_html(group_name))
    result = result.replace('<<ENTITY_NAME>>', escape_html(entity_name))
    result = result.replace('<<ENTITY_ID>>', escape_html(entity_id))
    result = result.replace('<<FISCAL_YEAR>>', escape_html(fiscal_year))
    result = result.replace('<<COUNTRY>>', escape_html(country))
    result = result.replace('<<BLUEPRINT_NAME>>', escape_html(blueprint_name))
    result = result.replace('<<DOCUMENT_TITLE>>', escape_html(doc_title))
    result = result.replace('<<DOCUMENT_SUBTITLE>>', escape_html(doc_subtitle))
    result = result.replace('<<DOCUMENT_META>>', doc_meta)

    # Stage
    stage = local_file.get('status', 'draft') if local_file else 'draft'
    stage_map = {'draft': 0, 'review': 1, 'final': 2}
    stage_idx = stage_map.get(stage, 0)
    result = result.replace('<<STAGE_DRAFT_CLASS>>', 'active' if stage_idx == 0 else '')
    result = result.replace('<<STAGE_REVIEW_CLASS>>', 'active' if stage_idx == 1 else '')
    result = result.replace('<<STAGE_FINAL_CLASS>>', 'active' if stage_idx == 2 else '')
    result = result.replace('<<STAGE_FILL_1>>', '100%' if stage_idx >= 1 else '0%')
    result = result.replace('<<STAGE_FILL_2>>', '100%' if stage_idx >= 2 else '0%')

    # Progress
    metrics = build_progress_metrics(blueprint, local_file)
    result = result.replace('<<TOTAL_SECTIONS>>', str(metrics['total']))
    result = result.replace('<<REVIEWED_COUNT>>', str(metrics['reviewed']))
    result = result.replace('<<SIGNOFF_COUNT>>', str(metrics['signoff']))
    result = result.replace('<<REVIEW_PCT>>', f'{metrics["review_pct"]}%')
    result = result.replace('<<SIGNOFF_PCT>>', f'{metrics["signoff_pct"]}%')

    # Jurisdiction SVG
    if not references_dir:
        references_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'references'
        )
    svg_html = build_jurisdiction_svg(country, references_dir)
    result = result.replace('<<JURISDICTION_SVG>>', svg_html)

    # Document sections
    sections_html = build_combined_sections_html(
        blueprint, resolved_sections, section_meta,
        data, entity.get('id', ''), transactions
    )
    result = result.replace('<<DOCUMENT_SECTIONS>>', sections_html)

    # General notes
    notes_html = build_general_notes_html(data, entity, transactions)
    result = result.replace('<<GENERAL_NOTES>>', notes_html)

    # Blueprint modal
    bp_html = build_blueprint_modal_html(blueprints_dir, blueprint)
    result = result.replace('<<BLUEPRINT_CARDS>>', bp_html)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Assemble a transfer pricing local file')
    parser.add_argument('--data', required=True, help='Path to group records JSON (data.json)')
    parser.add_argument('--blueprint', required=True, help='Path to entity blueprint JSON')
    parser.add_argument('--references', required=True, help='Path to references directory')
    parser.add_argument('--library', required=True, help='Path to firm library directory')
    parser.add_argument('--template', required=True, help='Path to template (LaTeX or HTML)')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--group-content', default=None,
                        help='Path to group content directory for @group/ references (e.g., [Group]/.records/content/)')
    parser.add_argument('--brand', default=None,
                        help='Path to brand.css design system (default: assets/brand.css relative to plugin root)')
    parser.add_argument('--format', choices=['pdf', 'html', 'md', 'report', 'combined'], default='pdf',
                        help='Output format: pdf (LaTeX → PDF), html (intake preview), md (markdown preview), report (annotated report view), combined (Workspace Editor)')
    parser.add_argument('--blueprints-dir', default=None,
                        help='Path to blueprints directory (for Workspace Editor blueprint modal)')
    parser.add_argument('--entity-content', default=None,
                        help='Path to entity content directory for @entity/ references')
    parser.add_argument('--section', default=None,
                        help='Render a single section in the editor (requires --format html). '
                             'Omit for dashboard overview. Example: --section group_overview')
    args = parser.parse_args()

    # --- Load inputs ---
    print(f"Loading records: {args.data}")
    data = load_json(args.data)

    print(f"Loading blueprint: {args.blueprint}")
    blueprint = load_json(args.blueprint)

    # --- Resolve blueprint inheritance ---
    if blueprint.get('based_on'):
        blueprint = resolve_blueprint_inheritance(
            blueprint, args.references, args.library,
            getattr(args, 'blueprints_dir', None)
        )

    print(f"Loading template: {args.template}")
    if not os.path.exists(args.template):
        print(f"Error: Template not found: {args.template}", file=sys.stderr)
        sys.exit(1)
    with open(args.template, 'r') as f:
        template_content = f.read()

    # Inject brand.css into HTML templates (has <<BRAND_CSS>> placeholder)
    if args.format in ('html', 'report', 'combined'):
        brand_path = args.brand or 'assets/brand.css'
        template_content = inject_brand_css(template_content, brand_path)

    # --- Find entity ---
    entity_id = blueprint.get('entity')
    if not entity_id:
        print("Error: Blueprint has no 'entity' field", file=sys.stderr)
        sys.exit(1)
    print(f"Looking up entity: {entity_id}")
    entity = find_entity(data, entity_id)

    # --- Validate ---
    validate_inputs(data, blueprint, entity)

    # --- Get transactions ---
    transactions = get_entity_transactions(data, entity_id)
    print(f"Found {len(transactions)} transactions for {entity.get('name')}")

    # --- Resolve content references ---
    group_content = getattr(args, 'group_content', None)
    entity_content = getattr(args, 'entity_content', None)
    print("Resolving content references...")
    resolved_sections = resolve_blueprint_sections(blueprint, args.references, args.library, group_content, entity_content)

    # --- Determine output filename ---
    entity_name = entity.get('name', 'entity')
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', ''))
    base_name = slugify(f"{entity_name}_Local_File_FY{fiscal_year}") if fiscal_year else slugify(f"{entity_name}_Local_File")

    # --- Write output ---
    os.makedirs(args.output, exist_ok=True)

    if args.format == 'report':
        # --- Annotated report view (X-ray mode) ---
        print("Resolving with layer metadata for report view...")
        resolved_sections_meta, section_meta = resolve_blueprint_sections_with_meta(
            blueprint, args.references, args.library, group_content, entity_content
        )
        print("Populating report view template...")
        report_base = slugify(f"{entity_name}_Report_View_FY{fiscal_year}") if fiscal_year else slugify(f"{entity_name}_Report_View")
        populated_report = populate_report_template(
            template_content, data, blueprint, entity, transactions,
            resolved_sections_meta, section_meta
        )
        report_path = os.path.join(args.output, f'{report_base}.html')
        with open(report_path, 'w') as f:
            f.write(populated_report)
        print(f"\nDone! Report view: {report_path}")

    elif args.format == 'md':
        # --- Markdown preview ---
        print("Populating markdown preview...")
        populated_md = populate_md_template(
            template_content, data, blueprint, entity, transactions, resolved_sections
        )
        md_path = os.path.join(args.output, f'{base_name}.md')
        with open(md_path, 'w') as f:
            f.write(populated_md)
        print(f"\nDone! Preview: {md_path}")

    elif args.format == 'html':
        # Detect mode: dashboard vs section editor vs legacy
        is_dashboard = '<<SECTION_CARDS>>' in template_content
        is_section_editor = '<<SECTION_CONTENT>>' in template_content

        if args.section and is_section_editor:
            # --- Section editor mode: render one section ---
            print(f"Resolving with layer metadata for section: {args.section}")
            resolved_sections_meta, section_meta = resolve_blueprint_sections_with_meta(
                blueprint, args.references, args.library, group_content, entity_content
            )
            if args.section not in resolved_sections_meta and not args.section.startswith('_auto_'):
                print(f"Warning: Section '{args.section}' not found in blueprint sections.", file=sys.stderr)
                avail = ', '.join(sorted(resolved_sections_meta.keys()))
                print(f"  Available sections: {avail}", file=sys.stderr)
            print(f"Populating section editor for: {args.section}")
            populated_html = populate_section_editor(
                template_content, data, blueprint, entity, transactions,
                resolved_sections_meta, section_meta, args.section
            )
            editor_base = slugify(f"{entity_name}_Section_{args.section}")
            html_path = os.path.join(args.output, f'{editor_base}.html')
            with open(html_path, 'w') as f:
                f.write(populated_html)
            print(f"\nDone! Section editor: {html_path}")

        elif is_dashboard:
            # --- Dashboard mode: overview of all sections ---
            print("Resolving with layer metadata for dashboard...")
            resolved_sections_meta, section_meta = resolve_blueprint_sections_with_meta(
                blueprint, args.references, args.library, group_content, entity_content
            )
            print("Populating section dashboard...")
            populated_html = populate_dashboard_template(
                template_content, data, blueprint, entity, transactions,
                resolved_sections_meta, section_meta
            )
            dashboard_base = slugify(f"{entity_name}_Dashboard_FY{fiscal_year}") if fiscal_year else slugify(f"{entity_name}_Dashboard")
            html_path = os.path.join(args.output, f'{dashboard_base}.html')
            with open(html_path, 'w') as f:
                f.write(populated_html)
            print(f"\nDone! Dashboard: {html_path}")

        else:
            # --- Editor view (dynamic sections with layer info) ---
            print("Resolving with layer metadata for editor...")
            resolved_sections_meta, section_meta = resolve_blueprint_sections_with_meta(
                blueprint, args.references, args.library, group_content, entity_content
            )
            print("Populating editor view...")
            populated_html = populate_html_template(
                template_content, data, blueprint, entity, transactions,
                resolved_sections_meta, section_meta
            )
            html_path = os.path.join(args.output, f'{base_name}.html')
            with open(html_path, 'w') as f:
                f.write(populated_html)
            print(f"\nDone! Editor: {html_path}")

    elif args.format == 'combined':
        # --- Workspace Editor (combined view) ---
        print("Resolving with layer metadata for Workspace Editor...")
        resolved_sections_meta, section_meta = resolve_blueprint_sections_with_meta(
            blueprint, args.references, args.library, group_content, entity_content
        )

        blueprints_dir = getattr(args, 'blueprints_dir', None)

        print("Populating Workspace Editor template...")
        populated = populate_combined_template(
            template_content, data, blueprint, entity, transactions,
            resolved_sections_meta, section_meta, blueprints_dir,
            references_dir=args.references
        )

        expert_base = slugify(f"{entity_name}_Workspace_Editor_FY{fiscal_year}") if fiscal_year else slugify(f"{entity_name}_Workspace_Editor")
        html_path = os.path.join(args.output, f'{expert_base}.html')
        with open(html_path, 'w') as f:
            f.write(populated)
        print(f"\nDone! Workspace Editor: {html_path}")

    else:
        # --- PDF (default) ---
        print("Populating LaTeX template...")
        populated_tex = populate_latex_template(
            template_content, data, blueprint, entity, transactions, resolved_sections
        )
        tex_path = os.path.join(args.output, f'{base_name}.tex')
        with open(tex_path, 'w') as f:
            f.write(populated_tex)
        print(f"Written: {tex_path}")

        print("Compiling PDF...")
        compile_pdf(tex_path, args.output)

        # Clean up LaTeX auxiliary files
        for ext in ['*.aux', '*.log', '*.out', '*.toc']:
            for aux_file in glob.glob(os.path.join(args.output, ext)):
                try:
                    os.remove(aux_file)
                except OSError:
                    pass  # Non-critical: aux files are just clutter

        pdf_path = os.path.join(args.output, f'{base_name}.pdf')
        print(f"\nDone! Output: {pdf_path}")


if __name__ == '__main__':
    main()

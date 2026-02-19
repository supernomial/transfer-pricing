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

Supports four output formats:
    --format pdf    → LaTeX → PDF (final deliverable)
    --format html   → HTML preview (live intake view in Cowork panel)
    --format report → Annotated report view with X-ray mode (layer annotations)
    --format md     → Markdown preview (fallback)

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

def load_json(path):
    """Load and return a JSON file."""
    if not os.path.exists(path):
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, 'r') as f:
        return json.load(f)


def resolve_reference(ref, references_dir, library_dir, group_content_dir=None):
    """Resolve a @references/, @library/, or @group/ content reference to actual text.

    Resolution order:
        @references/  → plugin references dir (Layer 1 — universal)
        @library/     → firm library dir (Layer 2 — firm-wide)
        @group/       → group content dir (Layer 3 — group-specific)
        plain text    → returned as-is (Layer 4 — entity-specific)
    """
    if ref.startswith('@references/'):
        rel_path = ref.replace('@references/', '')
        for ext in ['.md', '.json', '.txt', '']:
            full_path = os.path.join(references_dir, rel_path + ext)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    return f.read().strip()
        print(f"Warning: Could not resolve reference: {ref}", file=sys.stderr)
        return f"[UNRESOLVED: {ref}]"

    elif ref.startswith('@library/'):
        rel_path = ref.replace('@library/', '')
        for ext in ['.md', '.json', '.txt', '']:
            full_path = os.path.join(library_dir, rel_path + ext)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    return f.read().strip()
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
                    return f.read().strip()
        print(f"Warning: Could not resolve group content reference: {ref}", file=sys.stderr)
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
            'color': '#3b82f6',  # brand.css --sn-layer1
            'impact': 'Standard content from Supernomial — updates with plugin upgrades'
        }
    elif isinstance(raw_value, str) and raw_value.startswith('@library/'):
        return {
            'layer': 2, 'label': 'Firm Library',
            'source_path': raw_value, 'scope': 'firm',
            'color': '#a855f7',  # brand.css --sn-layer2
            'impact': 'From your firm library — shared across all clients'
        }
    elif isinstance(raw_value, str) and raw_value.startswith('@group/'):
        return {
            'layer': 3, 'label': 'Group',
            'source_path': raw_value, 'scope': 'group',
            'color': '#f59e0b',  # brand.css --sn-layer3
            'impact': 'Group-wide — editing affects all local files in this group'
        }
    else:
        # Plain text is entity-specific (Layer 4)
        return {
            'layer': 4, 'label': 'Entity',
            'source_path': None, 'scope': 'entity',
            'color': '#22c55e',  # brand.css --sn-layer4
            'impact': 'Entity-specific — this report only'
        }


def resolve_blueprint_sections(blueprint, references_dir, library_dir, group_content_dir=None):
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
                    parts.append(resolve_reference(element, references_dir, library_dir, group_content_dir))
                else:
                    parts.append(str(element))
            resolved[key] = '\n\n'.join(parts)
        elif isinstance(value, str):
            resolved[key] = resolve_reference(value, references_dir, library_dir, group_content_dir)
        else:
            resolved[key] = value
    return resolved


def resolve_blueprint_sections_with_meta(blueprint, references_dir, library_dir, group_content_dir=None):
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
                    parts.append(resolve_reference(element, references_dir, library_dir, group_content_dir))
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
            resolved[key] = resolve_reference(value, references_dir, library_dir, group_content_dir)
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


def build_editor_content_sections(resolved_sections, section_meta, blueprint):
    """Build dynamic HTML blocks for all blueprint content sections, organized by category.

    Each section gets an editable textarea with a layer dot and status badge.
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

            # Section content
            display_text = escape_html(text) if complete else ''
            placeholder = f'Write or ask Claude to draft: {label}'

            # Note line
            note_html = ''
            if note:
                note_html = (
                    f'<div style="font-size:11px;color:var(--sn-primary);font-style:italic;'
                    f'margin-top:6px">{escape_html(note)}</div>'
                )

            parts.append(
                f'<div class="section">\n'
                f'  <div class="section-header">\n'
                f'    <span class="section-label">{escape_html(label)}</span>\n'
                f'    <div style="display:flex;align-items:center;gap:10px">{layer_html}{badge}</div>\n'
                f'  </div>\n'
                f'  <div class="section-content">\n'
                f'    <textarea class="edit-area" id="{escape_html(key)}" '
                f'data-label="{escape_html(label)}" '
                f'placeholder="{escape_html(placeholder)}">{display_text}</textarea>\n'
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
    content_html = build_editor_content_sections(resolved_sections, section_meta, blueprint)
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
    color = meta.get('color', '#22c55e')
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

            if is_section_complete(text):
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
    """Replace all placeholders in the LaTeX template with actual values."""
    result = template_content

    # Entity fields
    result = result.replace('<<ENTITY_NAME>>', escape_latex(entity.get('name', 'Unknown Entity')))

    # Fiscal year: blueprint is the authority, fall back to entity
    fiscal_year = blueprint.get('fiscal_year', entity.get('fiscal_year', 'N/A'))
    result = result.replace('<<FISCAL_YEAR>>', str(fiscal_year))

    # Currency (use first transaction's currency, default EUR)
    currency = 'EUR'
    if transactions:
        currency = transactions[0].get('currency', 'EUR')
    result = result.replace('<<CURRENCY>>', currency)

    # Blueprint sections (already resolved)
    result = result.replace(
        '<<GROUP_OVERVIEW>>',
        escape_latex(resolved_sections.get('group_overview', '[No group overview provided]'))
    )
    result = result.replace(
        '<<ENTITY_INTRODUCTION>>',
        escape_latex(resolved_sections.get('entity_introduction', '[No entity introduction provided]'))
    )

    # Transaction table rows (already escaped inside build_transaction_rows)
    result = result.replace('<<TRANSACTION_ROWS>>', build_transaction_rows(transactions))

    return result


# ---------------------------------------------------------------------------
# PDF compilation
# ---------------------------------------------------------------------------

def compile_pdf(tex_path, output_dir):
    """Compile a .tex file to PDF using pdflatex."""
    try:
        subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-output-directory', output_dir, tex_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("PDF compiled successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling PDF. LaTeX log:\n{e.stdout}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: pdflatex not found on PATH.", file=sys.stderr)
        print("  If on macOS: brew install --cask basictex && eval \"$(/usr/libexec/path_helper)\"", file=sys.stderr)
        sys.exit(1)


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
                        help='Path to group content directory for @group/ references (e.g., [Group]/Records/content/)')
    parser.add_argument('--brand', default=None,
                        help='Path to brand.css design system (default: assets/brand.css relative to plugin root)')
    parser.add_argument('--format', choices=['pdf', 'html', 'md', 'report'], default='pdf',
                        help='Output format: pdf (LaTeX → PDF), html (intake preview), md (markdown preview), report (annotated report view)')
    parser.add_argument('--section', default=None,
                        help='Render a single section in the editor (requires --format html). '
                             'Omit for dashboard overview. Example: --section group_overview')
    args = parser.parse_args()

    # --- Load inputs ---
    print(f"Loading records: {args.data}")
    data = load_json(args.data)

    print(f"Loading blueprint: {args.blueprint}")
    blueprint = load_json(args.blueprint)

    print(f"Loading template: {args.template}")
    if not os.path.exists(args.template):
        print(f"Error: Template not found: {args.template}", file=sys.stderr)
        sys.exit(1)
    with open(args.template, 'r') as f:
        template_content = f.read()

    # Inject brand.css into HTML templates (has <<BRAND_CSS>> placeholder)
    if args.format in ('html', 'report'):
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
    print("Resolving content references...")
    resolved_sections = resolve_blueprint_sections(blueprint, args.references, args.library, group_content)

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
            blueprint, args.references, args.library, group_content
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
                blueprint, args.references, args.library, group_content
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
                blueprint, args.references, args.library, group_content
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
                blueprint, args.references, args.library, group_content
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
        for ext in ['*.aux', '*.log', '*.out']:
            for aux_file in glob.glob(os.path.join(args.output, ext)):
                try:
                    os.remove(aux_file)
                except OSError:
                    pass  # Non-critical: aux files are just clutter

        pdf_path = os.path.join(args.output, f'{base_name}.pdf')
        print(f"\nDone! Output: {pdf_path}")


if __name__ == '__main__':
    main()

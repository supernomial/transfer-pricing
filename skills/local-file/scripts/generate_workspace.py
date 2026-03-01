#!/usr/bin/env python3
"""Generate a Workspace Editor HTML file from a view JSON and template.

Injects brand.css (with base64-embedded fonts) into the HTML template and
sets the path to the view JSON file so the client-side JS can fetch it.
"""

import argparse
import base64
import os
import shutil
import sys


def build_font_faces(brand_dir):
    """Build @font-face declarations with base64-embedded Graphik font files."""
    fonts_dir = os.path.join(brand_dir, 'fonts')
    if not os.path.isdir(fonts_dir):
        return ''

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
    """Read brand.css and inject it as a <style> block at <!-- BRAND_CSS_INJECT -->."""
    if not os.path.exists(brand_path):
        print(f"Warning: brand.css not found at {brand_path}", file=sys.stderr)
        return template_content
    with open(brand_path, 'r') as f:
        brand_css = f.read()

    # Embed base64-encoded font faces
    if '<<FONT_FACES>>' in brand_css:
        brand_dir = os.path.dirname(brand_path)
        font_faces = build_font_faces(brand_dir)
        brand_css = brand_css.replace('<<FONT_FACES>>', font_faces)

    brand_block = f'<style>\n/* --- Brand design system --- */\n{brand_css}\n</style>'

    if '<!-- BRAND_CSS_INJECT -->' in template_content:
        return template_content.replace('<!-- BRAND_CSS_INJECT -->', brand_block)
    if '<<BRAND_CSS>>' in template_content:
        return template_content.replace('<<BRAND_CSS>>', brand_css)
    return template_content


def main():
    parser = argparse.ArgumentParser(description='Generate Workspace Editor HTML')
    parser.add_argument('--view-json', required=True, help='Path to view JSON file')
    parser.add_argument('--template', required=True, help='Path to combined_view.html template')
    parser.add_argument('--brand', required=True, help='Path to brand.css')
    parser.add_argument('--output', required=True, help='Output HTML file path')
    args = parser.parse_args()

    # Read template
    with open(args.template, 'r') as f:
        html = f.read()

    # Inject brand CSS with embedded fonts
    html = inject_brand_css(html, args.brand)

    # Read view JSON
    with open(args.view_json, 'r') as f:
        view_json_content = f.read()

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)

    # Embed JSON inline (works on file:// without CORS issues)
    html = html.replace('/* VIEW_DATA_INLINE */', view_json_content)

    # Also set the path for fetch-based loading (http:// environments)
    view_json_abs = os.path.abspath(args.view_json)
    view_json_basename = os.path.basename(view_json_abs)
    dest_json = os.path.join(output_dir, view_json_basename)

    if os.path.abspath(dest_json) != view_json_abs:
        shutil.copy2(view_json_abs, dest_json)
        print(f"Copied view JSON to {dest_json}")

    rel_path = os.path.relpath(dest_json, output_dir)
    html = html.replace('/* VIEW_DATA_PATH */', rel_path)

    # Write output
    with open(args.output, 'w') as f:
        f.write(html)

    print(f"Workspace Editor written to {args.output}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Fix YAML frontmatter in all markdown files.
Ensures title fields are properly quoted.
"""
import re
from pathlib import Path

def fix_frontmatter(content):
    """Fix YAML frontmatter by properly quoting title."""
    lines = content.split('\n')

    if not lines or lines[0] != '---':
        return content

    # Find the closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i] == '---':
            end_idx = i
            break

    if end_idx is None:
        return content

    # Process frontmatter lines
    for i in range(1, end_idx):
        line = lines[i]

        # Match title: ... line
        if line.startswith('title: '):
            title_value = line[7:]  # Remove 'title: '

            # Check if already quoted
            if title_value.startswith('"') and title_value.endswith('"'):
                continue
            if title_value.startswith("'") and title_value.endswith("'"):
                continue

            # Check if contains special YAML characters
            if any(char in title_value for char in ['[', ']', ':', '#', '@']):
                # Quote it with double quotes, escape any internal quotes
                title_value = title_value.replace('"', '\\"')
                lines[i] = f'title: "{title_value}"'

    return '\n'.join(lines)

def main():
    """Fix all markdown files in content directory."""
    content_dir = Path('content')

    if not content_dir.exists():
        print("Error: content directory not found")
        return

    # Find all markdown files
    md_files = list(content_dir.rglob('*.md'))
    print(f"Found {len(md_files)} markdown files")

    fixed_count = 0
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                original = f.read()

            fixed = fix_frontmatter(original)

            if fixed != original:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                print(f"Fixed: {md_file}")
                fixed_count += 1
        except Exception as e:
            print(f"Error processing {md_file}: {e}")

    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()

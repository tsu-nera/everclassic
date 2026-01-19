#!/usr/bin/env python3
"""
Extract WordPress posts from SQL dump and convert to Hugo markdown format.
"""
import re
import os
from datetime import datetime
from pathlib import Path
import html
from urllib.parse import unquote

def unescape_sql_string(s):
    """Unescape SQL string literal."""
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1]
    # Unescape SQL escapes
    s = s.replace("\\'", "'")
    s = s.replace('\\"', '"')
    s = s.replace('\\n', '\n')
    s = s.replace('\\r', '\r')
    s = s.replace('\\\\', '\\')
    return s

def html_to_markdown(html_content):
    """Convert HTML to Markdown (simple implementation)."""
    content = html_content

    # Convert blockquotes
    content = re.sub(r'<blockquote>\s*', '\n> ', content)
    content = re.sub(r'\s*</blockquote>', '\n\n', content)

    # Convert headings
    content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', content, flags=re.DOTALL)

    # Convert paragraphs
    content = re.sub(r'<p[^>]*>', '\n', content)
    content = re.sub(r'</p>', '\n', content)

    # Convert line breaks
    content = re.sub(r'<br\s*/?>', '\n', content)

    # Convert links
    content = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.DOTALL)

    # Convert strong/bold
    content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
    content = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', content, flags=re.DOTALL)

    # Convert em/italic
    content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
    content = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', content, flags=re.DOTALL)

    # Convert lists
    content = re.sub(r'<ul[^>]*>', '\n', content)
    content = re.sub(r'</ul>', '\n', content)
    content = re.sub(r'<ol[^>]*>', '\n', content)
    content = re.sub(r'</ol>', '\n', content)
    content = re.sub(r'<li[^>]*>', '- ', content)
    content = re.sub(r'</li>', '\n', content)

    # Remove remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)

    # Decode HTML entities
    content = html.unescape(content)

    # Clean up multiple newlines
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Remove &nbsp; entities that might remain
    content = content.replace('&nbsp;', ' ')
    content = content.replace('\xa0', ' ')

    return content.strip()

def parse_sql_row(row_str):
    """Parse a SQL row into fields."""
    fields = []
    current_field = ""
    in_quotes = False
    escape = False

    i = 0
    while i < len(row_str):
        char = row_str[i]

        if escape:
            current_field += char
            escape = False
            i += 1
            continue

        if char == '\\':
            escape = True
            current_field += char
            i += 1
            continue

        if char == "'":
            in_quotes = not in_quotes
            current_field += char
        elif char == ',' and not in_quotes:
            fields.append(current_field.strip())
            current_field = ""
        else:
            current_field += char

        i += 1

    if current_field:
        fields.append(current_field.strip())

    return fields

def extract_posts_from_sql(sql_file):
    """Extract posts from WordPress SQL dump."""
    print(f"Reading SQL file: {sql_file}")

    posts = []
    in_wp4_posts = False
    insert_buffers = []
    current_buffer = ""

    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Start collecting when we find the INSERT INTO statement
            if 'INSERT INTO `wp4_posts`' in line and 'VALUES' in line:
                in_wp4_posts = True
                # Extract the part after VALUES
                current_buffer = line.split('VALUES', 1)[1].strip()
                continue

            if in_wp4_posts:
                # Continue collecting until we hit a semicolon or UNLOCK
                if line.strip().startswith('UNLOCK') or line.strip().startswith('/*'):
                    in_wp4_posts = False
                    if current_buffer:
                        insert_buffers.append(current_buffer.rstrip().rstrip(';'))
                    break

                current_buffer += line

                # Check if line ends with semicolon (end of INSERT)
                if line.strip().endswith(';'):
                    in_wp4_posts = False
                    # Remove trailing semicolon and save buffer
                    insert_buffers.append(current_buffer.rstrip().rstrip(';'))
                    current_buffer = ""

    if not insert_buffers:
        print("No INSERT statement data found for wp4_posts")
        return []

    print(f"Found {len(insert_buffers)} INSERT statements")
    print(f"Parsing INSERT data...")

    # Process each INSERT buffer
    rows_data = []

    for buffer in insert_buffers:
        # Each row is in the format: (val1, val2, ..., valN),
        # We need to handle nested parentheses and quoted strings carefully

        current_row = []
        current_field = ""
        paren_depth = 0
        in_quotes = False
        escape = False

        for i, char in enumerate(buffer):
            if escape:
                current_field += char
                escape = False
                continue

            if char == '\\':
                escape = True
                current_field += char
                continue

            if char == "'" and not escape:
                in_quotes = not in_quotes
                current_field += char
                continue

            if in_quotes:
                current_field += char
                continue

            # Not in quotes
            if char == '(':
                if paren_depth == 0:
                    # Start of a new row
                    current_row = []
                    current_field = ""
                else:
                    current_field += char
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    # End of row
                    if current_field:
                        current_row.append(current_field.strip())
                        current_field = ""
                    if current_row:
                        rows_data.append(current_row)
                else:
                    current_field += char
            elif char == ',' and paren_depth == 1:
                # Field separator within a row
                current_row.append(current_field.strip())
                current_field = ""
            else:
                current_field += char

    print(f"Found {len(rows_data)} rows")

    # Process each row
    for fields in rows_data:
        if len(fields) < 21:
            continue

        # wp4_posts structure (index):
        # 0:ID, 1:post_author, 2:post_date, 3:post_date_gmt,
        # 4:post_content, 5:post_title, 6:post_excerpt,
        # 7:post_status, 8:comment_status, 9:ping_status,
        # 10:post_password, 11:post_name, 12:to_ping, 13:pinged,
        # 14:post_modified, 15:post_modified_gmt,
        # 16:post_content_filtered, 17:post_parent, 18:guid,
        # 19:menu_order, 20:post_type, 21:post_mime_type, 22:comment_count

        post_id = unescape_sql_string(fields[0])
        post_date = unescape_sql_string(fields[2])
        post_content = unescape_sql_string(fields[4])
        post_title = unescape_sql_string(fields[5])
        post_status = unescape_sql_string(fields[7])
        post_name = unescape_sql_string(fields[11])
        post_type = unescape_sql_string(fields[20]) if len(fields) > 20 else ''

        # Extract all posts (excluding revisions and auto-drafts)
        # Include: publish, draft, pending, private, future
        # Exclude: revision, auto-draft, inherit
        if post_type == 'post' and post_status not in ['inherit', 'auto-draft']:
            posts.append({
                'id': post_id,
                'title': post_title,
                'content': post_content,
                'date': post_date,
                'slug': post_name,
                'status': post_status,
            })
            print(f"  Found post ({post_status}): {post_title[:50]}...")

    print(f"\nExtracted {len(posts)} published posts")
    return posts

def generate_hugo_markdown(post, output_dir):
    """Generate Hugo markdown file from post data."""
    # Parse date
    try:
        date_obj = datetime.strptime(post['date'], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        print(f"Warning: Invalid date format for post {post['id']}: {post['date']}")
        return

    # Create output directory by year
    year = date_obj.year
    year_dir = Path(output_dir) / 'content' / 'posts' / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename: YYYY-MM-DD-title.md
    date_str = date_obj.strftime('%Y-%m-%d')
    # Sanitize title for filename - decode URL encoding first
    slug = post['slug'] if post['slug'] else post['title']
    # URL decode the slug
    slug = unquote(slug)
    # Use title if slug is empty or still encoded
    safe_title = slug if slug and not slug.startswith('%') else post['title']
    # Remove special characters but keep Japanese and alphanumeric
    safe_title = re.sub(r'[^\w\s\-、。！？]', '', safe_title)
    safe_title = re.sub(r'[\s]+', '-', safe_title)
    safe_title = safe_title.strip('-')

    # Limit filename length (Linux max is 255 bytes, UTF-8 Japanese is ~3 bytes/char)
    # Keep safe margin: date (10) + hyphen (1) + extension (3) = 14 bytes used
    # So limit title to ~80 chars to be safe (240 bytes for UTF-8)
    if len(safe_title) > 50:
        safe_title = safe_title[:50]

    filename = f"{date_str}-{safe_title}.md"
    filepath = year_dir / filename

    # Convert HTML content to Markdown
    markdown_content = html_to_markdown(post['content'])

    # Generate frontmatter
    # Add draft: true for non-published posts
    draft_status = 'draft: true\n' if post.get('status', 'publish') != 'publish' else ''

    frontmatter = f"""---
title: {post['title']}
date: {date_obj.strftime('%Y-%m-%d %H:%M:%S')}+00:00
url: /archives/{post['id']}
{draft_status}---

"""

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
        f.write(markdown_content)
        f.write('\n')

    print(f"Created: {filepath}")

def main():
    """Main function."""
    sql_file = '/tmp/LAA0187880-hb8oyh.sql'
    output_dir = '/home/tsu-nera/repo/everclassic'

    if not os.path.exists(sql_file):
        print(f"Error: SQL file not found: {sql_file}")
        return

    # Extract posts
    posts = extract_posts_from_sql(sql_file)

    if not posts:
        print("No posts found to convert")
        return

    # Generate Hugo markdown files
    print(f"\nGenerating Hugo markdown files...")
    for post in posts:
        generate_hugo_markdown(post, output_dir)

    print(f"\nDone! Generated {len(posts)} markdown files in {output_dir}/content/posts/")

if __name__ == '__main__':
    main()

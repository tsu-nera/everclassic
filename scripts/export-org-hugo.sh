#!/bin/bash

# Usage: ./export-org-hugo.sh <org-file-path>

if [ -z "$1" ]; then
    echo "Usage: $0 <org-file-path>"
    exit 1
fi

ORG_FILE="$1"

if [ ! -f "$ORG_FILE" ]; then
    echo "Error: File not found: $ORG_FILE"
    exit 1
fi

emacs --batch \
    --eval "(setq package-enable-at-startup nil)" \
    --eval "(require 'package)" \
    --eval "(add-to-list 'package-archives '(\"melpa\" . \"https://melpa.org/packages/\") t)" \
    --eval "(package-initialize)" \
    --eval "(unless (package-installed-p 'ox-hugo) (package-refresh-contents) (package-install 'ox-hugo))" \
    --eval "(require 'ox-hugo)" \
    "$ORG_FILE" \
    --eval "(org-hugo-export-to-md)"

# Remove author line from generated markdown files
HUGO_BASE_DIR="$HOME/repo/everclassic"
find "$HUGO_BASE_DIR/content/posts" -name "*.md" -type f -mmin -1 -exec sed -i '/^author = /d' {} \;

echo "Export completed for: $ORG_FILE"

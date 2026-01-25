#!/bin/bash
# 画像をリサイズしてWebP形式に変換するスクリプト
#
# 使い方: ./scripts/convert-image.sh 元画像パス 記事スラグ [説明]
# 例: ./scripts/convert-image.sh ~/Downloads/IMG_xxx.jpg gmo-sonic-2026
#      ./scripts/convert-image.sh ~/Downloads/IMG_xxx.jpg gmo-sonic-2026 stage

set -e

if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    echo "使い方: $0 <元画像パス> <記事スラグ> [説明]"
    echo "例: $0 ~/Downloads/IMG_xxx.jpg gmo-sonic-2026"
    echo "    $0 ~/Downloads/IMG_xxx.jpg gmo-sonic-2026 stage"
    exit 1
fi

SOURCE="$1"
SLUG="$2"
DESC="$3"

# 説明が指定されていない場合は連番を自動設定
if [ -z "$DESC" ]; then
    # 既存の画像から最大の連番を取得
    MAX_NUM=$(find static/images -name "${SLUG}-[0-9]*.webp" 2>/dev/null | \
              sed -n "s/.*${SLUG}-\([0-9]\+\)\.webp/\1/p" | \
              sort -n | tail -1)

    if [ -z "$MAX_NUM" ]; then
        DESC="01"
    else
        DESC=$(printf "%02d" $((MAX_NUM + 1)))
    fi
    echo "自動連番: $DESC"
fi

OUTPUT="static/images/${SLUG}-${DESC}.webp"

if [ ! -f "$SOURCE" ]; then
    echo "エラー: 元画像が見つかりません: $SOURCE"
    exit 1
fi

echo "変換中: $SOURCE -> $OUTPUT"
echo "  リサイズ: 幅1200px"
echo "  品質: 85"

# リサイズ(幅1200px) + WebP変換
convert "$SOURCE" -resize 1200x -quality 85 "$OUTPUT"

echo ""
echo "✓ 変換完了: $OUTPUT"
ls -lh "$OUTPUT"
echo ""
echo "orgファイルに以下を追加してください:"
echo "[[/images/${SLUG}-${DESC}.webp]]"

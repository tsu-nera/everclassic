#!/usr/bin/env python3
"""
記事のタイトルと内容を分析して、適切なカテゴリとタグを自動付与するスクリプト
"""
import os
import re
from pathlib import Path

# カテゴリ判定用のキーワード
CATEGORY_KEYWORDS = {
    "コンサート": ["n響", "N響", "都響", "読響", "オーケストラ", "フィル", "交響楽団", "定期公演", "コンサート", "演奏会"],
    "オペラ": ["オペラ", "二期会", "新国", "歌劇"],
    "バレエ": ["バレエ", "ballet"],
    "映画": ["映画", "映画館"],
    "音楽配信": ["ラジオ", "ottava", "klara", "インターネットラジオ", "配信"],
    "音楽スポット": ["名曲喫茶", "ライオン"],
    "ブログ運営": ["everclassic", "EverClassic", "ブログ", "ドメイン", "周年"],
    "電子音楽": ["電子音楽", "テクノ", "コンピュータ音楽", "reaper"],
}

# タグ用のキーワード（指揮者、オーケストラ、作曲家）
TAG_KEYWORDS = {
    # 指揮者
    "インバル": ["インバル"],
    "デュトワ": ["デュトワ", "デュドワ"],
    "メルクル": ["メルクル"],
    "マゼール": ["マゼール"],
    "ブロムシュテット": ["ブロムシュテット"],
    "ゲルギエフ": ["ゲルギエフ"],
    "ソヒエフ": ["ソヒエフ"],
    "ノリントン": ["ノリントン"],
    "チョン・ミョンフン": ["チョン", "ミュンフン"],
    "ドゥダメル": ["ドゥダメル"],
    "飯守泰次郎": ["飯守"],
    "ジンマン": ["ジンマン"],
    "ルイージ": ["ルイージ"],
    "上岡敏之": ["上岡"],

    # オーケストラ
    "N響": ["n響", "N響", "NHK交響楽団"],
    "都響": ["都響", "東京都交響楽団"],
    "読響": ["読響", "読売日本交響楽団"],
    "マリインスキー": ["マリインスキー"],
    "フランス放送フィル": ["フランス放送", "フランス国立"],
    "スカラ座": ["スカラ座"],

    # 作曲家
    "マーラー": ["マーラー"],
    "ブラームス": ["ブラームス"],
    "ワーグナー": ["ワーグナー"],
    "ショスタコーヴィチ": ["ショスタコ"],
    "チャイコフスキー": ["チャイ"],
    "ラヴェル": ["ラヴェル"],
    "ベートーヴェン": ["ベートーヴェン", "ベートーベン"],
    "ブルックナー": ["ブルックナー"],
    "ドヴォルザーク": ["ドボルザーク", "ドヴォルザーク"],
    "プロコフィエフ": ["プロコ"],
    "ヴェルディ": ["ヴェルディ"],
    "サン・サーンス": ["サン・サーンス"],
}

def read_frontmatter_and_content(filepath):
    """ファイルのフロントマターと内容を読み取る"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # フロントマターと本文を分離
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None, content

    frontmatter = parts[1]
    body = parts[2]

    return frontmatter, body

def extract_title(frontmatter):
    """フロントマターからタイトルを抽出"""
    match = re.search(r'title:\s*(.+)', frontmatter)
    return match.group(1).strip() if match else ""

def determine_category(title, content):
    """タイトルと内容からカテゴリを判定"""
    # タイトルのスコアを重視
    title_scores = {}
    content_scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        title_scores[category] = sum(title.count(keyword) for keyword in keywords)
        content_scores[category] = sum(content[:1000].count(keyword) for keyword in keywords)

    # 総合スコア（タイトルを3倍重視）
    total_scores = {}
    for category in CATEGORY_KEYWORDS.keys():
        total_scores[category] = title_scores[category] * 3 + content_scores[category]

    # 「ブログ運営」は特別扱い：タイトルに明確なキーワードがある場合のみ
    if total_scores.get("ブログ運営", 0) > 0:
        blog_keywords = ["ブログ", "ドメイン", "周年"]
        if not any(keyword in title for keyword in blog_keywords):
            total_scores["ブログ運営"] = 0

    # スコアが最も高いカテゴリを返す
    if max(total_scores.values()) > 0:
        return max(total_scores, key=total_scores.get)
    return "その他"

def extract_tags(title, content):
    """タイトルと内容からタグを抽出"""
    text = title + " " + content
    tags = []

    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)

    return tags

def update_frontmatter(filepath):
    """記事のフロントマターにカテゴリとタグを追加"""
    frontmatter, body = read_frontmatter_and_content(filepath)

    if frontmatter is None:
        print(f"警告: {filepath} のフロントマターが見つかりません")
        return

    title = extract_title(frontmatter)
    category = determine_category(title, body)
    tags = extract_tags(title, body)

    # 既存のcategoryとtagsを削除
    frontmatter_lines = frontmatter.strip().split('\n')
    new_frontmatter_lines = []
    for line in frontmatter_lines:
        if not line.startswith('categories:') and not line.startswith('tags:'):
            new_frontmatter_lines.append(line)

    # 新しいカテゴリとタグを追加
    new_frontmatter_lines.append(f'categories: ["{category}"]')
    if tags:
        tags_str = ", ".join(f'"{tag}"' for tag in tags)
        new_frontmatter_lines.append(f'tags: [{tags_str}]')

    # ファイルを更新
    new_content = "---\n" + "\n".join(new_frontmatter_lines) + "\n---" + body

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✓ {Path(filepath).name}: カテゴリ={category}, タグ={tags}")

def main():
    """メイン処理"""
    posts_dir = Path("/home/tsu-nera/repo/everclassic/content/posts")

    # すべてのマークダウンファイルを取得
    md_files = list(posts_dir.rglob("*.md"))

    print(f"処理対象: {len(md_files)}ファイル\n")

    for filepath in sorted(md_files):
        update_frontmatter(filepath)

    print(f"\n完了: {len(md_files)}ファイルを処理しました")

if __name__ == "__main__":
    main()

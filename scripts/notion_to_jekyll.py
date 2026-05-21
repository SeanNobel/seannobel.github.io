#!/usr/bin/env python3
"""Convert a Notion Markdown export to a Jekyll post.

Usage:
    python scripts/notion_to_jekyll.py <path-to-notion-export>
    python scripts/notion_to_jekyll.py <path-to-notion-export> --date 2026-05-21 --slug my-post

`<path-to-notion-export>` can be either:
  - the .zip downloaded from Notion ("Export" -> "Markdown & CSV")
  - or an already-unzipped folder

Output:
  - _posts/YYYY-MM-DD-<slug>-ja.md  (Japanese post, front-matter ready)
  - assets/blog/<slug>/...           (images referenced in the post)

The English translation step is intentionally not handled here; it will be
added later as a `--translate` flag that produces the matching `-en.md`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = REPO_ROOT / "_posts"
ASSETS_BLOG_DIR = REPO_ROOT / "assets" / "blog"

NOTION_HASH_RE = re.compile(r"\s+[0-9a-f]{20,}$", re.IGNORECASE)
IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")


def strip_notion_hash(name: str) -> str:
    return NOTION_HASH_RE.sub("", name).strip()


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text or "post"


def find_export_root(path: Path) -> Path:
    """Return the directory containing the top-level .md file of the export."""
    if path.is_file() and path.suffix.lower() == ".md":
        return path.parent

    candidates = sorted(p for p in path.glob("*.md") if p.is_file())
    if candidates:
        return path

    subdirs = [p for p in path.iterdir() if p.is_dir()]
    if len(subdirs) == 1:
        return find_export_root(subdirs[0])

    raise SystemExit(f"Could not find a Notion .md file inside {path}")


def find_post_md(export_root: Path) -> Path:
    mds = sorted(p for p in export_root.glob("*.md") if p.is_file())
    if not mds:
        raise SystemExit(f"No .md file found in {export_root}")
    if len(mds) > 1:
        print(f"Warning: multiple .md files found in export; using {mds[0].name}", file=sys.stderr)
    return mds[0]


def extract_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def strip_title_line(md_text: str) -> str:
    lines = md_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            return "\n".join(lines[i + 1:]).lstrip("\n")
    return md_text


def rewrite_images(md_text: str, export_root: Path, slug: str) -> str:
    """Copy any locally-referenced images into assets/blog/<slug>/ and rewrite paths."""
    dest_dir = ASSETS_BLOG_DIR / slug

    def _replace(match: re.Match[str]) -> str:
        alt = match.group("alt")
        src = match.group("src").strip()
        if src.startswith(("http://", "https://", "/")):
            return match.group(0)

        decoded = urllib.parse.unquote(src)
        local_path = (export_root / decoded).resolve()
        try:
            local_path.relative_to(export_root.resolve())
        except ValueError:
            return match.group(0)

        if not local_path.exists():
            print(f"Warning: image not found, skipping: {decoded}", file=sys.stderr)
            return match.group(0)

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / local_path.name
        shutil.copy2(local_path, dest_file)
        rel_url = f"/assets/blog/{slug}/{local_path.name}"
        return f"![{alt}]({rel_url})"

    return IMAGE_RE.sub(_replace, md_text)


def render_front_matter(title: str, date: dt.date, slug: str) -> str:
    title_escaped = title.replace('"', '\\"')
    return (
        "---\n"
        "layout: post\n"
        f'title: "{title_escaped}"\n'
        f"date: {date.isoformat()}\n"
        "lang: ja\n"
        f"slug_id: {slug}\n"
        f"permalink: /blog-ja/{slug}/\n"
        "---\n\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a Notion Markdown export to a Jekyll post.")
    parser.add_argument("path", type=Path, help="Path to a Notion export zip or unzipped folder.")
    parser.add_argument("--date", type=str, default=None, help="Override post date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--slug", type=str, default=None, help="Override the auto-generated slug.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.path.exists():
        raise SystemExit(f"Path does not exist: {args.path}")

    tmpdir_obj: tempfile.TemporaryDirectory | None = None
    if args.path.is_file() and args.path.suffix.lower() == ".zip":
        tmpdir_obj = tempfile.TemporaryDirectory(prefix="notion-export-")
        with zipfile.ZipFile(args.path) as zf:
            zf.extractall(tmpdir_obj.name)
        export_root = find_export_root(Path(tmpdir_obj.name))
    else:
        export_root = find_export_root(args.path)

    md_path = find_post_md(export_root)
    md_text = md_path.read_text(encoding="utf-8")

    fallback_name = strip_notion_hash(md_path.stem)
    title = extract_title(md_text, fallback_name)
    slug = args.slug or slugify(strip_notion_hash(title))

    if args.date:
        post_date = dt.date.fromisoformat(args.date)
    else:
        post_date = dt.date.today()

    body = strip_title_line(md_text)
    body = rewrite_images(body, export_root, slug)

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = POSTS_DIR / f"{post_date.isoformat()}-{slug}-ja.md"

    if out_path.exists():
        print(f"Warning: overwriting existing post: {out_path.name}", file=sys.stderr)

    out_path.write_text(render_front_matter(title, post_date, slug) + body, encoding="utf-8")

    print(f"Wrote {out_path.relative_to(REPO_ROOT)}")
    if (ASSETS_BLOG_DIR / slug).exists():
        print(f"Copied images to {(ASSETS_BLOG_DIR / slug).relative_to(REPO_ROOT)}/")

    # TODO: --translate flag. When implemented, generate
    # _posts/YYYY-MM-DD-<slug>-en.md sharing the same slug_id, with
    # permalink /blog/<slug>/ and translated title/body.

    if tmpdir_obj is not None:
        tmpdir_obj.cleanup()


if __name__ == "__main__":
    main()

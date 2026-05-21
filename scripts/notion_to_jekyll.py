#!/usr/bin/env python3
"""Convert a Notion Markdown export to a Jekyll post.

Usage:
    python scripts/notion_to_jekyll.py _posts/<category>/<notion-export>.zip

The input path must live under `_posts/<category>/` — the parent folder name
becomes the post's category. Output goes into the same folder:

    _posts/<category>/<YYYY-MM-DD>-<slug>.md      (Japanese — the source of truth)

Images referenced in the post are copied to `assets/blog/<slug>/` and their
paths are rewritten to absolute site paths.

For the English version, paste the generated Japanese markdown into Claude
Desktop, translate it manually, and save the result alongside as
`<YYYY-MM-DD>-<slug>-en.md` with `lang: en` and `permalink: /blog/<slug>/`
in the front matter.
"""

from __future__ import annotations

import argparse
import datetime as dt
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


def _is_junk(path: Path) -> bool:
    """Filter out macOS resource fork files and __MACOSX folders."""
    return "__MACOSX" in path.parts or path.name.startswith("._")


def extract_all_zips(root: Path) -> None:
    """Recursively extract any zip files under `root` in place.

    Notion's "ExportBlock" downloads wrap the actual markdown export inside a
    nested `*-Part-N.zip`, so we need to keep unpacking until no zips remain.
    """
    while True:
        nested_zips = [
            z for z in root.rglob("*.zip")
            if z.is_file() and not _is_junk(z)
        ]
        if not nested_zips:
            return
        for z in nested_zips:
            dest = z.with_suffix("")
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dest)
            z.unlink()


def find_export_root(path: Path) -> Path:
    """Return the directory containing the shallowest Notion .md file."""
    if path.is_file() and path.suffix.lower() == ".md":
        return path.parent

    candidates = [
        p for p in path.rglob("*.md")
        if p.is_file() and not _is_junk(p)
    ]
    if not candidates:
        raise SystemExit(f"Could not find a Notion .md file inside {path}")
    candidates.sort(key=lambda p: (len(p.parts), p.name))
    return candidates[0].parent


def find_post_md(export_root: Path) -> Path:
    mds = sorted(p for p in export_root.glob("*.md") if p.is_file() and not _is_junk(p))
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


def derive_category(input_path: Path) -> tuple[str, Path]:
    """Return (category_name, category_dir) given an input path under _posts/<category>/."""
    resolved = input_path.resolve()
    category_dir = resolved.parent
    posts_resolved = POSTS_DIR.resolve()
    if category_dir.parent != posts_resolved:
        raise SystemExit(
            f"Input must live under _posts/<category>/. Got: {input_path}\n"
            f"Place the Notion export under _posts/<category>/ first."
        )
    return category_dir.name, category_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a Notion Markdown export to a Jekyll post.")
    parser.add_argument("path", type=Path, help="Path to a Notion export zip or unzipped folder, located under _posts/<category>/.")
    parser.add_argument("--date", type=str, default=None, help="Override post date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--slug", type=str, default=None, help="Override the auto-generated slug.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.path.exists():
        raise SystemExit(f"Path does not exist: {args.path}")

    category, category_dir = derive_category(args.path)

    tmpdir_obj: tempfile.TemporaryDirectory | None = None
    if args.path.is_file() and args.path.suffix.lower() == ".zip":
        tmpdir_obj = tempfile.TemporaryDirectory(prefix="notion-export-")
        with zipfile.ZipFile(args.path) as zf:
            zf.extractall(tmpdir_obj.name)
        extract_all_zips(Path(tmpdir_obj.name))
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

    ja_path = category_dir / f"{post_date.isoformat()}-{slug}.md"
    if ja_path.exists():
        print(f"Warning: overwriting existing post: {ja_path.relative_to(REPO_ROOT)}", file=sys.stderr)
    ja_path.write_text(render_front_matter(title, post_date, slug) + body, encoding="utf-8")
    print(f"Wrote {ja_path.relative_to(REPO_ROOT)}  (category: {category})")
    if (ASSETS_BLOG_DIR / slug).exists():
        print(f"Copied images to {(ASSETS_BLOG_DIR / slug).relative_to(REPO_ROOT)}/")

    if tmpdir_obj is not None:
        tmpdir_obj.cleanup()


if __name__ == "__main__":
    main()

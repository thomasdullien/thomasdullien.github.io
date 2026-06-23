#!/usr/bin/env python3
"""Import public Blogger posts into Quarto post directories."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


FEED_URL = "https://addxorrol.blogspot.com/feeds/posts/default"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def feed_url(start_index: int, max_results: int, published_min: str) -> str:
    params = {
        "alt": "json",
        "start-index": str(start_index),
        "max-results": str(max_results),
        "published-min": published_min,
    }
    return f"{FEED_URL}?{urllib.parse.urlencode(params)}"


def parse_date(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def slugify(title: str) -> str:
    slug = title.lower()
    slug = html.unescape(slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:72].strip("-") or "post"


def alternate_url(entry: dict) -> str:
    for link in entry.get("link", []):
        if link.get("rel") == "alternate":
            return link.get("href", "")
    return ""


def blogger_id(entry: dict) -> str:
    value = entry.get("id", {}).get("$t", "")
    return value.rsplit("-", 1)[-1] if value else ""


IFRAME_RE = re.compile(r"<iframe\b.*?</iframe>", re.IGNORECASE | re.DOTALL)


def preserve_iframes(source_html: str) -> tuple[str, list[str]]:
    iframes: list[str] = []

    def replacement(match: re.Match[str]) -> str:
        token = f"BLOGGER_IFRAME_PLACEHOLDER_{len(iframes)}"
        iframes.append(match.group(0))
        return f"<p>{token}</p>"

    return IFRAME_RE.sub(replacement, source_html), iframes


def restore_iframes(markdown: str, iframes: list[str]) -> str:
    for index, iframe in enumerate(iframes):
        token = f"BLOGGER_IFRAME_PLACEHOLDER_{index}"
        escaped_token = token.replace("_", r"\_")
        raw_block = "\n".join(
            [
                "::: {.video-embed}",
                "```{=html}",
                iframe,
                "```",
                ":::",
            ]
        )
        markdown = markdown.replace(token, raw_block)
        markdown = markdown.replace(escaped_token, raw_block)
    return markdown


def convert_html_to_markdown(pandoc: str, source_html: str) -> str:
    source_html, iframes = preserve_iframes(source_html)
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "post.html"
        md_path = Path(tmp) / "post.md"
        html_path.write_text(source_html, encoding="utf-8")
        subprocess.run(
            [
                pandoc,
                str(html_path),
                "-f",
                "html",
                "-t",
                "markdown_strict+raw_html+pipe_tables+backtick_code_blocks+auto_identifiers",
                "--wrap=preserve",
                "-o",
                str(md_path),
            ],
            check=True,
        )
        return restore_iframes(md_path.read_text(encoding="utf-8").strip(), iframes)


def front_matter(entry: dict, published: datetime, updated: datetime) -> str:
    title = entry.get("title", {}).get("$t", "Untitled")
    categories = [c.get("term") for c in entry.get("category", []) if c.get("term")]
    lines = [
        "---",
        f"title: {yaml_string(title)}",
        f"date: {published.date().isoformat()}",
        f"date-modified: {updated.date().isoformat()}",
        f"original-url: {yaml_string(alternate_url(entry))}",
    ]
    if blogger_id(entry):
        lines.append(f"blogger-id: {yaml_string(blogger_id(entry))}")
    if categories:
        lines.append("categories:")
        for category in categories:
            lines.append(f"  - {yaml_string(category)}")
    lines.extend(["---", ""])
    return "\n".join(lines)


def iter_entries(since: str, page_size: int = 100):
    start = 1
    while True:
        data = fetch_json(feed_url(start, page_size, since))
        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break
        for entry in entries:
            yield entry
        start += len(entries)


def import_posts(args: argparse.Namespace) -> int:
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    seen_dirs: set[Path] = set()

    for entry in iter_entries(args.since):
        published = parse_date(entry["published"]["$t"])
        updated = parse_date(entry["updated"]["$t"])
        title = entry.get("title", {}).get("$t", "Untitled")
        post_dir = out_dir / f"{published.date().isoformat()}-{slugify(title)}"
        suffix = 2
        while post_dir in seen_dirs:
            post_dir = out_dir / f"{published.date().isoformat()}-{slugify(title)}-{suffix}"
            suffix += 1
        seen_dirs.add(post_dir)

        index = post_dir / "index.qmd"
        if index.exists() and not args.force:
            print(f"skip existing {index}", file=sys.stderr)
            continue

        content_html = entry.get("content", {}).get("$t", "")
        markdown = convert_html_to_markdown(args.pandoc, content_html)
        body = front_matter(entry, published, updated) + markdown + "\n"

        post_dir.mkdir(parents=True, exist_ok=True)
        index.write_text(body, encoding="utf-8")
        print(index)
        count += 1

    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2022-01-01T00:00:00Z")
    parser.add_argument("--output", default="posts")
    parser.add_argument("--pandoc", default="pandoc")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    count = import_posts(args)
    print(f"Imported {count} posts.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

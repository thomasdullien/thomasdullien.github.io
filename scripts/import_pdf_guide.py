#!/usr/bin/env python3
"""Convert the entrepreneurship PDF text layer into a Quarto guide page."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


MAIN_HEADINGS = {
    "Introduction",
    "Reasons to become an entrepreneur",
    "The choice of your target market",
    "Funding, Fundraising, Investors etc.",
    "Product and customers",
    "Hiring",
    "Marketing",
    "Sales",
    "Running the business",
    "Delegating work and personal growth",
    "The end, the exit, the denouement",
}

SUB_HEADINGS = {
    "Bootstrapping? VC? What other options?",
    "Understanding risk-return payoffs",
    "Venture fund napkin math",
    "First-time founders and the risk-return tradeoff",
    "Ways of addressing this",
    "You are going the VC route - what does this mean?",
    "Early Exits, and why they are harmful for the VC",
    "Understanding the VC’s job, and VC dynamics",
    "The value of verbal commitments",
    "Top-tier firms can wait",
    "If you get funded, a competitor will get funded, too",
    "The importance of “momentum” and managing the perception thereof",
    "Investors are neither your friends nor your therapists",
    "How to run a fundraise",
    "How NOT to run a fundraise",
    "Investor updates and “potential investor” updates",
    "Picking the right VC",
    "Technology vs. product, starting from a problem vs. from a solution",
    "Product ideation",
    "Top-line growth, bottom-line-growth, and everything else",
    "The user persona and the buyer persona",
    "How does this product get (user/buyer) promoted?",
    "A shining example: The FinOps stunt",
    "Development partners",
    "The importance of clickable prototypes",
    "Design is not how it looks, Design is how it works",
    "Interviewing",
    "Managing people",
    "Conflicts in teams and the “capuchin monkey hierarchy”",
    "Having to fire people",
    "Recognizing expertise where you don’t have expertise",
    "How does this sales stuff work?",
    "Managing a funnel",
    "When to hire a sales professional",
    "Your three balance sheets",
    "Cofounder relationships: The inverse marriage",
    "Splitting equity between cofounder",
    "Relationship between founders and investors",
    "Consider getting a coach",
    "You and your employees",
    "Equity and ownership with employees",
}

SUBSUB_HEADINGS = {
    "The VC claim of providing “value-add”",
    "The “big gorilla” theory of picking VCs",
    "Your relationship with the GP",
    "“Why aren’t you raising now?”",
    "Early-stage valuation",
    "Make room for non-operational conversations",
}


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_reader():
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.path.insert(0, str(Path(".tools/python")))
        from pypdf import PdfReader
    return PdfReader


def extract_pages(pdf: Path) -> list[str]:
    reader_cls = load_reader()
    reader = reader_cls(str(pdf))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text(extraction_mode="layout") or "")
    return pages


def strip_page_header(line: str) -> bool:
    return bool(re.search(r"Halvar’s Guide to Entrepreneurship, v0\.1 - page \d+", line))


def clean_lines(pages: list[str]) -> list[str]:
    cleaned: list[str] = []
    for page_index, page in enumerate(pages):
        page_lines = page.splitlines()
        if page_index == 1:
            continue
        if page_index == 0:
            trimmed = []
            for line in page_lines:
                if re.match(r"\s*Halvar’s guide to Entrepreneurship\s+\d+\s*$", line):
                    break
                trimmed.append(line)
            page_lines = trimmed
        for line in page_lines:
            if strip_page_header(line):
                continue
            if not line.strip():
                cleaned.append("")
                continue
            cleaned.append(line.rstrip())
    return cleaned


def is_heading(text: str) -> tuple[int, str] | None:
    if text in MAIN_HEADINGS:
        return (2, text)
    if text in SUB_HEADINGS:
        return (3, text)
    if text in SUBSUB_HEADINGS:
        return (4, text)
    return None


def normalize_inline(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = text.replace(" -- ", " — ")
    return text


def emit_paragraph(out: list[str], paragraph: list[str]) -> None:
    if not paragraph:
        return
    text = normalize_inline(" ".join(paragraph))
    if text:
        out.extend([text, ""])
    paragraph.clear()


def convert_lines_to_markdown(lines: list[str]) -> str:
    out: list[str] = []
    paragraph: list[str] = []
    list_item: list[str] = []
    in_ordered_list = False

    def flush_list() -> None:
        nonlocal in_ordered_list
        if list_item:
            out.append(normalize_inline(" ".join(list_item)))
            list_item.clear()
        if in_ordered_list:
            out.append("")
        in_ordered_list = False

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            emit_paragraph(out, paragraph)
            flush_list()
            continue

        if stripped in {"Halvar’s guide to Entrepreneurship", "version 0.1 - June 23rd 2026"}:
            continue
        if stripped.startswith("Feedback, comments, corrections:"):
            continue
        if stripped.startswith("Author:"):
            continue

        heading = is_heading(stripped)
        if heading:
            emit_paragraph(out, paragraph)
            flush_list()
            level, text = heading
            out.extend([f"{'#' * level} {text}", ""])
            continue

        ordered_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if ordered_match:
            emit_paragraph(out, paragraph)
            flush_list()
            in_ordered_list = True
            list_item.append(f"{ordered_match.group(1)}. {ordered_match.group(2)}")
            continue

        bullet_match = re.match(r"^[-•]\s+(.*)$", stripped)
        if bullet_match:
            emit_paragraph(out, paragraph)
            flush_list()
            out.append(f"- {normalize_inline(bullet_match.group(1))}")
            continue

        if in_ordered_list and raw.startswith(" "):
            list_item.append(stripped)
            continue

        flush_list()
        paragraph.append(stripped)

    emit_paragraph(out, paragraph)
    flush_list()
    return "\n".join(out).strip() + "\n"


def write_guide(pdf: Path, output: Path, pdf_name: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    target_pdf = output / pdf_name
    shutil.copy2(pdf, target_pdf)

    body = convert_lines_to_markdown(clean_lines(extract_pages(pdf)))
    front_matter = "\n".join(
        [
            "---",
            'title: "Halvar’s Guide to Entrepreneurship"',
            'subtitle: "Version 0.1"',
            'description: "Thomas Dullien’s guide to software and SaaS B2B entrepreneurship."',
            "date: 2026-06-23",
            'author: "Thomas Dullien"',
            "toc: true",
            "---",
            "",
            f"[Download the original PDF]({pdf_name}).",
            "",
        ]
    )
    (output / "index.qmd").write_text(front_matter + body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--output", default="guides/entrepreneurship")
    parser.add_argument("--pdf-name", default="halvars-guide-to-entrepreneurship.pdf")
    args = parser.parse_args()
    write_guide(Path(args.pdf), Path(args.output), args.pdf_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

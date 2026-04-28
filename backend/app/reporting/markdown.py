"""Small safe Markdown renderer used for reports."""

from __future__ import annotations

import re
from html import escape


REPORT_SECTIONS = ("原因", "判据", "结论", "建议")


def normalize_report_markdown(markdown: str) -> str:
    """Normalize report headings so each fixed section title stands alone."""

    normalized = markdown.strip().replace("\r\n", "\n")
    for section in REPORT_SECTIONS:
        normalized = re.sub(
            rf"(?m)^##\s*{section}\s*[：:：-]\s*(\S.*)$",
            rf"## {section}\n\n\1",
            normalized,
        )
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _inline(text: str) -> str:
    rendered = escape(text)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2" target="_blank" rel="noreferrer">\1</a>',
        rendered,
    )
    return rendered


def markdown_to_html(markdown: str) -> str:
    """Render a conservative Markdown subset to safe HTML."""

    markdown = normalize_report_markdown(markdown)
    lines = markdown.splitlines()
    html: list[str] = []
    paragraph: list[str] = []
    list_open = False
    code_open = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            html.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            html.append("</ul>")
            list_open = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            if code_open:
                html.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                code_open = False
            else:
                code_open = True
            continue

        if code_open:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            close_list()
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            html.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue

        list_item = re.match(r"^[-*]\s+(.+)$", stripped)
        if list_item:
            flush_paragraph()
            if not list_open:
                html.append("<ul>")
                list_open = True
            html.append(f"<li>{_inline(list_item.group(1))}</li>")
            continue

        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    if code_open:
        html.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")

    body = "\n".join(html)
    return (
        "<html><body class='report-document' "
        "style='font-family:Segoe UI, PingFang SC, Microsoft YaHei, sans-serif;'>"
        f"{body}</body></html>"
    )

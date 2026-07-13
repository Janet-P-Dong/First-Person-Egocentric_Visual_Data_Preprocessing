from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


SOURCE = Path("/Users/janet/Downloads/Dissertation Results Framework /Dissertation Results Framework.md")
SOURCE_IMAGE_DIR = SOURCE.parent / "Images_attachments"
OUT_DIR = Path("/Users/janet/Documents/TDSEM Developmental Calibration Research/outputs/dissertation_results_latex")
OUT_FILE = OUT_DIR / "Dissertation_Results_Framework.tex"
OUT_IMAGE_DIR = OUT_DIR / "Images_attachments"


PREAMBLE = r"""\documentclass[12pt]{report}

\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{float}
\usepackage{caption}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{hyperref}
\usepackage{xurl}
\usepackage{setspace}

\graphicspath{{Images_attachments/}}
\onehalfspacing

\begin{document}

\begin{titlepage}
\centering
\vspace*{2in}
{\Large Dissertation Results Framework\par}
\vspace{1in}
{\large Converted from Markdown draft\par}
\end{titlepage}

\tableofcontents
\clearpage
"""


ENDING = r"""

\end{document}
"""


SPECIALS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
}


GREEK = {
    "Δ": r"\Delta",
    "χ": r"\chi",
    "²": r"$^2$",
    "≤": r"$\leq$",
    "≥": r"$\geq$",
    "−": "-",
    "–": "--",
    "→": r"$\rightarrow$",
    "≈": r"$\approx$",
    "ω": r"$\omega$",
    "β": r"$\beta$",
}


def unescape_markdown(text: str) -> str:
    text = text.replace(r"\.", ".")
    text = text.replace(r"\-", "-")
    text = text.replace(r"\_", "_")
    text = text.replace(r"\[", "[")
    text = text.replace(r"\]", "]")
    text = text.replace(r"\(", "(")
    text = text.replace(r"\)", ")")
    text = text.replace(r"\<", "<")
    text = text.replace(r"\>", ">")
    text = text.replace(r"\*", "*")
    return text


def strip_markdown_emphasis(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = text.replace("~~", "")
    return text


def escape_latex(text: str) -> str:
    text = unescape_markdown(text)
    text = strip_markdown_emphasis(text)
    for old, new in GREEK.items():
        text = text.replace(old, new)
    text = text.replace("\\", r"\textbackslash{}")
    escaped = []
    for char in text:
        escaped.append(SPECIALS.get(char, char))
    return "".join(escaped)


def convert_inline(text: str) -> str:
    text = unescape_markdown(text)
    text = text.replace("~~", "")
    placeholders: list[str] = []

    def hold(value: str) -> str:
        placeholders.append(value)
        return f"@@HOLD{len(placeholders) - 1}@@"

    def bold(match: re.Match[str]) -> str:
        return hold(r"\textbf{" + escape_latex(match.group(1)) + "}")

    def italic(match: re.Match[str]) -> str:
        return hold(r"\emph{" + escape_latex(match.group(1)) + "}")

    text = re.sub(r"\*\*(.*?)\*\*", bold, text)
    text = re.sub(r"\*(.*?)\*", italic, text)
    text = text.replace("\\", r"\textbackslash{}")
    for old, new in GREEK.items():
        text = text.replace(old, new)
    escaped = []
    for char in text:
        escaped.append(SPECIALS.get(char, char))
    text = "".join(escaped)
    for idx, value in enumerate(placeholders):
        text = text.replace(f"@@HOLD{idx}@@", value)
    return text


def heading_command(level: int, title: str) -> str:
    clean = escape_latex(title.strip())
    if level == 1:
        return f"\\chapter*{{{clean}}}\n\\addcontentsline{{toc}}{{chapter}}{{{clean}}}"
    if level == 2:
        return f"\\section*{{{clean}}}\n\\addcontentsline{{toc}}{{section}}{{{clean}}}"
    if level == 3:
        return f"\\subsection*{{{clean}}}\n\\addcontentsline{{toc}}{{subsection}}{{{clean}}}"
    if level == 4:
        return f"\\subsubsection*{{{clean}}}\n\\addcontentsline{{toc}}{{subsubsection}}{{{clean}}}"
    return f"\\paragraph*{{{clean}}}"


def image_block(alt: str, path: str, pending_caption: str | None = None) -> str:
    clean_path = path.replace("%20", " ")
    if clean_path.endswith(".gif"):
        clean_path = clean_path[:-4] + ".png"
    caption_source = pending_caption or (Path(clean_path).name if alt else Path(clean_path).name)
    caption = escape_latex(caption_source)
    include_path = rf"\detokenize{{{clean_path}}}"
    return "\n".join(
        [
            r"\begin{figure}[H]",
            r"\centering",
            rf"\includegraphics[width=0.92\textwidth]{{{include_path}}}",
            rf"\caption{{{caption}}}",
            r"\end{figure}",
        ]
    )


def convert() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if SOURCE_IMAGE_DIR.exists():
        shutil.copytree(SOURCE_IMAGE_DIR, OUT_IMAGE_DIR, dirs_exist_ok=True)
        for gif in OUT_IMAGE_DIR.glob("*.gif"):
            png = gif.with_suffix(".png")
            if not png.exists() and shutil.which("sips"):
                subprocess.run(
                    ["sips", "-s", "format", "png", str(gif), "--out", str(png)],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    output: list[str] = [PREAMBLE]
    pending_images: list[tuple[str, str]] = []

    def flush_images(caption: str | None = None) -> None:
        nonlocal pending_images
        if not pending_images:
            return
        for alt, path in pending_images:
            output.append(image_block(alt, path, caption))
            output.append("")
        pending_images = []

    for raw in lines:
        line = raw.rstrip()
        image = re.match(r"!\[(.*?)\]\((.*?)\)", line)
        if image:
            pending_images.append((image.group(1), image.group(2)))
            continue

        if pending_images and re.match(r"^(Figure|FIGURE)\b", unescape_markdown(line).strip()):
            flush_images(unescape_markdown(line).strip())
            continue
        flush_images()

        if not line.strip():
            output.append("")
            continue

        heading = re.match(r"^(#{1,5})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            title = strip_markdown_emphasis(unescape_markdown(heading.group(2))).strip()
            if title:
                output.append(heading_command(level, title))
                output.append("")
            continue

        bullet = re.match(r"^-\s+(.*)$", line)
        if bullet:
            output.append(r"\begin{itemize}")
            output.append(rf"\item {convert_inline(bullet.group(1))}")
            output.append(r"\end{itemize}")
            output.append("")
            continue

        output.append(convert_inline(line))
        output.append("")

    flush_images()
    output.append(ENDING)
    OUT_FILE.write_text("\n".join(output), encoding="utf-8")


if __name__ == "__main__":
    convert()

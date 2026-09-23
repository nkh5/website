import fitz
import json
import re
import sys
import html
from pathlib import Path


PDF_PATH = Path(
    sys.argv[1] if len(sys.argv) > 1
    else "assets/Nicholas_Hu_Resume.pdf"
)

OUTPUT_PATH = Path(
    sys.argv[2] if len(sys.argv) > 2
    else "data/resume.json"
)


MONTH = (
    r"(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)"
)

DATE_RANGE_RE = re.compile(
    rf"^{MONTH}\s+\d{{4}}\s*[–—-]\s*"
    rf"(?:{MONTH}\s+\d{{4}}|Present)$"
)

BULLET_RE = re.compile(r"^[•●▪]\s*")
LOCATION_RE = re.compile(r"^.+,\s*[A-Z]{2}$")


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def line_from_spans(spans):
    """
    Build both plain text and HTML for one PDF line.

    PyMuPDF flag bit 16 = bold.
    We escape all PDF text, then add <strong> only ourselves.
    """

    plain_parts = []
    html_parts = []

    meaningful_spans = [
        span for span in spans
        if span.get("text", "").strip()
    ]

    for span in spans:
        text = span.get("text", "")

        if not text:
            continue

        plain_parts.append(text)

        escaped = html.escape(text)

        is_bold = bool(span.get("flags", 0) & 16)

        if is_bold and text.strip():
            html_parts.append(f"<strong>{escaped}</strong>")
        else:
            html_parts.append(escaped)

    plain = clean_text("".join(plain_parts))
    html_text = "".join(html_parts).strip()

    # Determine whether the entire meaningful line is bold/italic.
    all_bold = (
        bool(meaningful_spans)
        and all(span.get("flags", 0) & 16 for span in meaningful_spans)
    )

    all_italic = (
        bool(meaningful_spans)
        and all(span.get("flags", 0) & 2 for span in meaningful_spans)
    )

    return {
        "text": plain,
        "html": html_text,
        "all_bold": all_bold,
        "all_italic": all_italic
    }


def extract_pdf_lines(pdf_path):
    """
    Extract lines while preserving font information.
    """

    document = fitz.open(pdf_path)

    lines = []

    for page in document:
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):

            if "lines" not in block:
                continue

            for pdf_line in block["lines"]:
                line = line_from_spans(pdf_line.get("spans", []))

                if line["text"]:
                    lines.append(line)

    document.close()

    return lines


SECTION_HEADINGS = {
    "education",
    "skills",
    "experience",
    "projects",
    "leadership",
    "relevant coursework"
}


def normalize_heading(text):
    """
    Normalize section headings so:
    SKILLS
    Skills
    skills

    all match the same way.
    """
    return clean_text(text).casefold()


def get_section(lines, start_heading):
    """
    Get everything after start_heading until the next
    recognized resume section.

    This makes section order irrelevant.
    """

    start_key = normalize_heading(start_heading)

    start = None

    for i, line in enumerate(lines):
        if normalize_heading(line["text"]) == start_key:
            start = i + 1
            break

    if start is None:
        raise RuntimeError(
            f'Could not find "{start_heading}" section.'
        )

    # Find the next known resume section.
    for i in range(start, len(lines)):

        text = normalize_heading(lines[i]["text"])

        if text in SECTION_HEADINGS:
            return lines[start:i]

    # If this is the last section, go to end of PDF.
    return lines[start:]

def strip_bullet(text):
    return BULLET_RE.sub("", text, count=1).strip()


def strip_bullet_html(value):
    return re.sub(
        r"^[•●▪]\s*",
        "",
        value,
        count=1
    ).strip()


def collect_bullets(lines):
    """
    Turn resume bullets + wrapped lines into one website paragraph.
    Bold formatting from the PDF is retained.
    """

    bullets_plain = []
    bullets_html = []

    current_plain = None
    current_html = None

    for line in lines:
        text = line["text"]

        # New bullet
        if BULLET_RE.match(text):

            if current_plain is not None:
                bullets_plain.append(current_plain.strip())
                bullets_html.append(current_html.strip())

            current_plain = strip_bullet(text)
            current_html = strip_bullet_html(line["html"])

            continue

        # Ignore entry-header material.
        if (
            line["all_bold"]
            or line["all_italic"]
            or LOCATION_RE.match(text)
            or DATE_RANGE_RE.match(text)
        ):
            continue

        # Wrapped continuation of current bullet.
        if current_plain is not None:
            current_plain += " " + text
            current_html += " " + line["html"]

    if current_plain is not None:
        bullets_plain.append(current_plain.strip())
        bullets_html.append(current_html.strip())

    return {
        "description": " ".join(bullets_plain),
        "description_html": " ".join(bullets_html)
    }


def parse_experience(lines):
    """
    Handles the actual resume format:

    Rockwell Automation
    Milwaukee, WI
    Software Development Intern
    June 2026 – August 2026
    • Bullet...
    """

    entries = []

    date_indices = [
        i for i, line in enumerate(lines)
        if DATE_RANGE_RE.match(line["text"])
    ]

    current_organization = None
    previous_date_index = -1

    for position, date_index in enumerate(date_indices):

        if date_index == 0:
            continue

        role_index = date_index - 1
        role = lines[role_index]["text"]
        dates = lines[date_index]["text"]

        # Search since the previous role for a new fully-bold organization.
        search_start = previous_date_index + 1

        organization_candidates = []

        for candidate in lines[search_start:role_index]:
            text = candidate["text"]

            if (
                candidate["all_bold"]
                and not BULLET_RE.match(text)
                and not LOCATION_RE.match(text)
            ):
                organization_candidates.append(text)

        if organization_candidates:
            current_organization = organization_candidates[-1]

        if not current_organization:
            raise RuntimeError(
                f"Could not determine organization for role: {role}"
            )

        # Description ends immediately before the next role.
        if position + 1 < len(date_indices):
            next_date_index = date_indices[position + 1]
            description_end = next_date_index - 1
        else:
            description_end = len(lines)

        description_lines = lines[
            date_index + 1:description_end
        ]

        descriptions = collect_bullets(description_lines)

        entries.append({
            "organization": current_organization,
            "role": role,
            "dates": dates,
            **descriptions
        })

        previous_date_index = date_index

    return entries


def parse_leadership(lines):
    """
    Handles:

    OwlSat (Rice CubeSat Club) | Hardware Team Lead
    September 2023 – Present
    • Bullet...
    """

    entries = []

    date_indices = [
        i for i, line in enumerate(lines)
        if DATE_RANGE_RE.match(line["text"])
    ]

    for position, date_index in enumerate(date_indices):

        if date_index == 0:
            continue

        heading = lines[date_index - 1]["text"]
        dates = lines[date_index]["text"]

        if "|" not in heading:
            raise RuntimeError(
                f"Expected leadership heading containing '|': {heading}"
            )

        organization, role = heading.rsplit("|", 1)

        if position + 1 < len(date_indices):
            next_date_index = date_indices[position + 1]
            description_end = next_date_index - 1
        else:
            description_end = len(lines)

        description_lines = lines[
            date_index + 1:description_end
        ]

        descriptions = collect_bullets(description_lines)

        entries.append({
            "organization": organization.strip(),
            "role": role.strip(),
            "dates": dates,
            **descriptions
        })

    return entries


def validate(data):
    """
    Fail rather than publishing broken resume data.
    """

    if not data["experience"]:
        raise RuntimeError(
            "No Experience entries were extracted."
        )

    if not data["leadership"]:
        raise RuntimeError(
            "No Leadership entries were extracted."
        )

    for section in ("experience", "leadership"):

        for entry in data[section]:

            for key in (
                "organization",
                "role",
                "dates",
                "description",
                "description_html"
            ):

                if not entry.get(key):
                    raise RuntimeError(
                        f"Missing {key} in {section}: {entry}"
                    )


def main():

    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"Resume PDF not found: {PDF_PATH}"
        )

    print(f"Reading {PDF_PATH}")

    lines = extract_pdf_lines(PDF_PATH)

    experience_lines = get_section(
    lines,
    "Experience"
    )

    leadership_lines = get_section(
    lines,
    "Leadership"
    )
    data = {
        "experience": parse_experience(experience_lines),
        "leadership": parse_leadership(leadership_lines)
    }

    validate(data)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

        file.write("\n")

    print(
        f"Generated {OUTPUT_PATH}: "
        f"{len(data['experience'])} experience entries, "
        f"{len(data['leadership'])} leadership entries."
    )


if __name__ == "__main__":
    main()

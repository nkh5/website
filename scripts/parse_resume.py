import fitz
import json
import re
import sys
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

DATE_RANGE = (
    rf"{MONTH}\s+\d{{4}}\s*[–—-]\s*"
    rf"(?:{MONTH}\s+\d{{4}}|Present)"
)

ROLE_DATE_RE = re.compile(
    rf"^(?P<title>.+?)\s+(?P<dates>{DATE_RANGE})$"
)

BULLET_RE = re.compile(r"^[•●▪]\s*")


def clean_line(line):
    """Normalize whitespace from PDF extraction."""
    return re.sub(r"\s+", " ", line).strip()


def strip_location(text):
    """
    Removes location suffixes used by the current resume, such as:
        Rockwell Automation Milwaukee, WI
        Rice University ECE & Baylor College of Medicine Houston, TX

    This assumes the city is one word, which matches the current resume.
    """
    return re.sub(
        r"\s+\S+,\s+[A-Z]{2}$",
        "",
        text
    ).strip()


def extract_pdf_lines(pdf_path):
    """Extract all text lines from the resume PDF."""
    document = fitz.open(pdf_path)

    lines = []

    for page in document:
        text = page.get_text("text")

        for line in text.splitlines():
            line = clean_line(line)

            if line:
                lines.append(line)

    document.close()

    return lines


def get_section(lines, start_heading, end_heading):
    """
    Return all lines between two resume section headings.
    """

    try:
        start = lines.index(start_heading) + 1
    except ValueError:
        raise RuntimeError(
            f'Could not find "{start_heading}" section in resume.'
        )

    try:
        end = lines.index(end_heading, start)
    except ValueError:
        raise RuntimeError(
            f'Could not find "{end_heading}" after "{start_heading}".'
        )

    return lines[start:end]


def finalize_entry(entry):
    """Convert collected bullet text into website-ready data."""

    if not entry:
        return None

    bullets = [
        clean_line(bullet)
        for bullet in entry.pop("_bullets", [])
        if clean_line(bullet)
    ]

    # Website currently uses one paragraph instead of resume bullets.
    entry["description"] = " ".join(bullets)

    return entry


def parse_experience(lines):
    """
    Parse entries such as:

    Rockwell Automation Milwaukee, WI
    Software Development Intern June 2026 – August 2026
    • Bullet...
    • Bullet...

    Software Development Intern June 2025 – August 2025
    • Bullet...

    Rice University ECE & Baylor College of Medicine Houston, TX
    ML Student Researcher November 2024 – Present
    • Bullet...
    """

    entries = []

    current_organization = None
    current_entry = None

    i = 0

    while i < len(lines):
        line = lines[i]

        role_match = ROLE_DATE_RE.match(line)

        # ---------------------------------
        # Resume bullet
        # ---------------------------------

        if BULLET_RE.match(line):

            if current_entry is not None:
                bullet = BULLET_RE.sub("", line).strip()
                current_entry["_bullets"].append(bullet)

            i += 1
            continue

        # ---------------------------------
        # Role + dates
        # ---------------------------------

        if role_match:

            if current_entry is not None:
                entries.append(finalize_entry(current_entry))

            current_entry = {
                "organization": current_organization or "",
                "role": role_match.group("title").strip(),
                "dates": role_match.group("dates").strip(),
                "_bullets": []
            }

            i += 1
            continue

        # ---------------------------------
        # Detect organization line
        #
        # Organization lines are immediately
        # followed by a role/date line.
        # ---------------------------------

        next_line = lines[i + 1] if i + 1 < len(lines) else ""

        if ROLE_DATE_RE.match(next_line):

            if current_entry is not None:
                entries.append(finalize_entry(current_entry))
                current_entry = None

            current_organization = strip_location(line)

            i += 1
            continue

        # ---------------------------------
        # Wrapped bullet continuation
        # ---------------------------------

        if (
            current_entry is not None
            and current_entry["_bullets"]
        ):

            current_entry["_bullets"][-1] += " " + line

        i += 1

    if current_entry is not None:
        entries.append(finalize_entry(current_entry))

    return entries


def parse_leadership(lines):
    """
    Parse entries such as:

    OwlSat (Rice CubeSat Club) | Hardware Team Lead September 2023 – Present
    • Bullet...

    Rice IEEE | Class Representative August 2023 – Present
    • Bullet...
    """

    entries = []
    current_entry = None

    for line in lines:

        # ---------------------------------
        # Bullet
        # ---------------------------------

        if BULLET_RE.match(line):

            if current_entry is not None:
                bullet = BULLET_RE.sub("", line).strip()
                current_entry["_bullets"].append(bullet)

            continue

        # ---------------------------------
        # Organization | Role + Dates
        # ---------------------------------

        role_match = ROLE_DATE_RE.match(line)

        if role_match:

            title = role_match.group("title").strip()
            dates = role_match.group("dates").strip()

            if "|" not in title:
                # If format changes unexpectedly,
                # don't generate incorrect content.
                raise RuntimeError(
                    f"Leadership entry does not contain '|': {line}"
                )

            organization, role = title.rsplit("|", 1)

            if current_entry is not None:
                entries.append(finalize_entry(current_entry))

            current_entry = {
                "organization": organization.strip(),
                "role": role.strip(),
                "dates": dates,
                "_bullets": []
            }

            continue

        # ---------------------------------
        # Wrapped bullet continuation
        # ---------------------------------

        if (
            current_entry is not None
            and current_entry["_bullets"]
        ):

            current_entry["_bullets"][-1] += " " + line

    if current_entry is not None:
        entries.append(finalize_entry(current_entry))

    return entries


def validate(data):
    """
    Fail instead of publishing suspicious/empty data.
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

            required = (
                "organization",
                "role",
                "dates",
                "description"
            )

            for key in required:

                if not entry.get(key):
                    raise RuntimeError(
                        f"Missing {key} in {section} entry: {entry}"
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
        "Experience",
        "Projects"
    )

    leadership_lines = get_section(
        lines,
        "Leadership",
        "Skills"
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

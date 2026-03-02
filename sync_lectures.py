"""
Auto-sync Fathom class recordings to the GitHub Pages lectures page.

Fetches STCM140 recordings from the Fathom API, compares against
what's already in docs/lectures.md, and appends new entries.
Commits and pushes if anything changed.
"""

import os
import re
import subprocess
import sys
import time
from datetime import datetime

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LECTURES_MD = os.path.join(SCRIPT_DIR, "docs", "lectures.md")

API_KEY = os.environ.get("FATHOM_API_KEY", "")
BASE_URL = "https://api.fathom.ai/external/v1"
CUTOFF_DATE = "2026-01-01"

TITLE_KEYWORDS = ["stcm140", "stcm 140", "stcm-140"]
TITLE_KEYWORDS_SECONDARY = ["multimedia production for strategic"]


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def fetch_class_meetings():
    """Fetch STCM140 recordings from Fathom API."""
    headers = {"X-Api-Key": API_KEY}
    params = {
        "include_summary": "true",
        "created_after": f"{CUTOFF_DATE}T00:00:00Z",
    }

    all_meetings = []
    cursor = None

    while True:
        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            f"{BASE_URL}/meetings", headers=headers, params=params
        )

        if response.status_code == 429:
            log("Rate limited, waiting 60 seconds...")
            time.sleep(60)
            continue

        if response.status_code != 200:
            log(f"API error: {response.status_code} - {response.text}")
            return []

        data = response.json()
        all_meetings.extend(data.get("items", []))

        cursor = data.get("next_cursor")
        if not cursor:
            break

    # Filter to class meetings only
    class_meetings = []
    for m in all_meetings:
        title = m.get("title", "").lower()
        if any(kw in title for kw in TITLE_KEYWORDS):
            class_meetings.append(m)
        elif any(kw in title for kw in TITLE_KEYWORDS_SECONDARY):
            class_meetings.append(m)

    # Sort by date ascending
    class_meetings.sort(key=lambda m: m.get("created_at", ""))
    return class_meetings


def extract_clean_title(title):
    """Remove STCM140 prefix and date suffixes from title."""
    title = re.sub(r'^STCM\s*140\s*[:|\-]\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*\([^)]*\d+[^)]*\)\s*$', '', title)
    return title.strip()


def get_summary_text(meeting):
    """Extract summary text, handling dict/string/None."""
    summary = meeting.get("default_summary")
    if summary is None:
        return ""
    if isinstance(summary, dict):
        return summary.get("markdown_formatted", "")
    if isinstance(summary, str):
        return summary
    return ""


def format_date_short(iso_date):
    """Convert ISO date to 'Feb 10' format (short month, no leading zero)."""
    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    return dt.strftime("%b %-d")


def parse_existing_dates(content):
    """Extract dates already present in the recordings table."""
    dates = set()
    # Match table rows like "| Feb 10 | ..."
    for match in re.finditer(r'^\|\s*(\w+\s+\d+)\s*\|', content, re.MULTILINE):
        dates.add(match.group(1).strip())
    return dates


GENERIC_TITLES = [
    "multimedia production for strategic communications",
    "multimedia production for strategic",
    "multimedia production",
]


def extract_meeting_purpose(raw_summary):
    """Extract the Meeting Purpose line from a Fathom summary.

    Used as a fallback title when the recording has the generic course name.
    """
    if not raw_summary:
        return ""
    in_purpose = False
    for line in raw_summary.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## Meeting Purpose"):
            in_purpose = True
            continue
        if in_purpose:
            if stripped.startswith("## "):
                break  # Hit next section
            if stripped:
                text = re.sub(r'\[([^\]]+)\]\(https?://[^)]*\)', r'\1', stripped)
                return text.strip()
    return ""


def get_descriptive_title(title, raw_summary):
    """Get a descriptive title, falling back to Meeting Purpose if generic."""
    clean = extract_clean_title(title)
    if clean.lower() in GENERIC_TITLES:
        purpose = extract_meeting_purpose(raw_summary)
        if purpose:
            # Capitalize first letter, strip trailing period
            return purpose[0].upper() + purpose[1:].rstrip(".")
    return clean


def strip_fathom_links(text):
    """Remove Fathom share links from markdown, keeping the link text.

    Fathom wraps bullets in links like [**Bold text:** rest](https://fathom.video/...).
    This strips the URL while preserving the display text.
    """
    # [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\(https?://fathom\.video/[^)]*\)', r'\1', text)
    return text.strip()


def parse_summary_into_sections(raw_summary):
    """Parse Fathom's structured markdown summary into key takeaways and topics.

    Fathom summaries have sections like:
      ## Key Takeaways
        - [**Point:** Description](https://fathom.video/...)
      ## Topics
        ### Topic Name
          - [**Sub-point**](url)

    We extract the Key Takeaways bullets directly and the Topics
    top-level section headers as topic entries.
    """
    if not raw_summary:
        return [], []

    lines = raw_summary.strip().split("\n")
    takeaways = []
    topics = []
    current_section = None

    for line in lines:
        stripped = line.strip()

        # Track which section we're in
        if stripped.startswith("## Key Takeaways"):
            current_section = "takeaways"
            continue
        elif stripped.startswith("## Topics"):
            current_section = "topics"
            continue
        elif stripped.startswith("## "):
            current_section = None
            continue

        if current_section == "takeaways":
            # Top-level bullets (2-4 spaces indent + dash)
            if re.match(r'^\s{0,4}-\s+', line):
                bullet = re.sub(r'^\s*-\s+', '', line).strip()
                bullet = strip_fathom_links(bullet)
                if bullet:
                    takeaways.append(bullet)

        elif current_section == "topics":
            # Topic section headers (### Topic Name)
            if stripped.startswith("### "):
                topic_name = stripped[4:].strip()
                topic_name = strip_fathom_links(topic_name)
                # Collect the first sub-bullet as a description
                topics.append({"name": topic_name, "details": []})
            # Top-level bullet under a topic section
            elif re.match(r'^\s{0,4}-\s+', line) and topics:
                bullet = re.sub(r'^\s*-\s+', '', line).strip()
                bullet = strip_fathom_links(bullet)
                if bullet and len(topics[-1]["details"]) < 2:
                    topics[-1]["details"].append(bullet)

    return takeaways[:3], topics


def build_table_row(date_short, clean_title, share_url):
    """Build a markdown table row for the recordings table."""
    link = f"[Watch]({share_url})" if share_url else "Coming soon"
    return f"| {date_short} | {clean_title} | {link} |"


def build_summary_section(date_short, clean_title, takeaways, topics):
    """Build a markdown summary section matching existing lectures.md format."""
    lines = [f"### {date_short} — {clean_title}", ""]

    if takeaways:
        lines.append("**Key takeaways:**")
        for t in takeaways:
            lines.append(f"- {t}")
        lines.append("")

    if topics:
        lines.append("**Topics covered:**")
        for t in topics:
            if isinstance(t, dict):
                name = t["name"]
                details = t.get("details", [])
                if details:
                    lines.append(f"- **{name}** — {details[0]}")
                else:
                    lines.append(f"- **{name}**")
            else:
                lines.append(f"- {t}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def update_lectures_md(new_recordings):
    """Insert new recordings into lectures.md.

    Table rows go in chronological order (before the '*Recordings are added...' note).
    Summary sections go in reverse chronological order (newest first, after the
    'Lecture summaries' heading).
    """
    with open(LECTURES_MD, "r") as f:
        content = f.read()

    lines = content.split("\n")
    changed = False

    # --- Insert table rows ---
    # Find the line with "*Recordings are added after each class session.*"
    note_idx = None
    for i, line in enumerate(lines):
        if "*Recordings are added" in line:
            note_idx = i
            break

    if note_idx is not None:
        # Insert new rows just before the note line (after the last table row)
        # Walk backwards from note_idx to find where to insert
        insert_idx = note_idx
        # Skip blank lines between last table row and note
        while insert_idx > 0 and lines[insert_idx - 1].strip() == "":
            insert_idx -= 1

        # Insert in chronological order (already sorted)
        new_table_lines = []
        for rec in new_recordings:
            row = build_table_row(rec["date_short"], rec["clean_title"], rec["share_url"])
            new_table_lines.append(row)
            log(f"  Table row: {rec['date_short']} - {rec['clean_title']}")

        if new_table_lines:
            for j, row in enumerate(new_table_lines):
                lines.insert(insert_idx + j, row)
            changed = True

    # --- Insert summary sections ---
    # Find "## Lecture summaries" heading
    summaries_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Lecture summaries"):
            summaries_idx = i
            break

    if summaries_idx is not None:
        # Find the description paragraph after the heading, then insert after it
        # Skip: heading, blank line, description paragraph, blank line
        insert_after = summaries_idx + 1
        while insert_after < len(lines) and lines[insert_after].strip() == "":
            insert_after += 1
        # Skip the description paragraph
        while insert_after < len(lines) and lines[insert_after].strip() != "":
            insert_after += 1
        # Skip trailing blank line
        while insert_after < len(lines) and lines[insert_after].strip() == "":
            insert_after += 1

        # Insert in chronological order at the same position — each new insert
        # pushes previous ones down, producing reverse chronological order
        for rec in new_recordings:
            section = build_summary_section(
                rec["date_short"], rec["clean_title"],
                rec["takeaways"], rec["topics"]
            )
            section_lines = section.split("\n")
            for j, sl in enumerate(section_lines):
                lines.insert(insert_after + j, sl)
            log(f"  Summary: {rec['date_short']} - {rec['clean_title']}")
            changed = True

    if changed:
        with open(LECTURES_MD, "w") as f:
            f.write("\n".join(lines))

    return changed


def git_commit_and_push(new_recordings):
    """Commit changes to lectures.md and push to origin."""
    os.chdir(SCRIPT_DIR)

    # Stage
    subprocess.run(["git", "add", "docs/lectures.md"], check=True)

    # Check if there are staged changes
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True
    )
    if result.returncode == 0:
        log("No staged changes — skipping commit")
        return False

    # Build commit message
    dates = [r["date_short"] for r in new_recordings]
    if len(dates) == 1:
        msg = f"Add {dates[0]} lecture recording and summary"
    else:
        msg = f"Add lecture recordings: {', '.join(dates)}"

    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)
    log(f"Pushed: {msg}")
    return True


def main():
    if not API_KEY:
        log("Error: FATHOM_API_KEY not set")
        sys.exit(1)

    log("Fetching STCM140 recordings from Fathom...")
    meetings = fetch_class_meetings()
    log(f"Found {len(meetings)} class recordings")

    if not meetings:
        log("No class recordings found")
        return

    # Parse existing dates from lectures.md
    with open(LECTURES_MD) as f:
        content = f.read()
    existing_dates = parse_existing_dates(content)
    log(f"Already in lectures.md: {sorted(existing_dates)}")

    # Find new recordings
    new_recordings = []
    for m in meetings:
        created = m.get("created_at", "")
        if not created:
            continue

        date_short = format_date_short(created)
        if date_short in existing_dates:
            continue

        summary_text = get_summary_text(m)
        clean_title = get_descriptive_title(m.get("title", "Untitled"), summary_text)
        takeaways, topics = parse_summary_into_sections(summary_text)
        share_url = m.get("share_url", "")

        new_recordings.append({
            "date_short": date_short,
            "clean_title": clean_title,
            "share_url": share_url,
            "takeaways": takeaways,
            "topics": topics,
        })

    if not new_recordings:
        log("No new recordings to add")
        return

    log(f"New recordings to add: {len(new_recordings)}")
    for r in new_recordings:
        log(f"  {r['date_short']} — {r['clean_title']}")

    # Update the markdown file
    changed = update_lectures_md(new_recordings)

    if changed:
        git_commit_and_push(new_recordings)
        log("Done — lectures page updated")
    else:
        log("No changes made to lectures.md")


if __name__ == "__main__":
    main()

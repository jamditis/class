"""
Fetch STCM140 class recordings from Fathom API.
Filters for class-related meetings from Spring 2026 semester.
"""

import requests
import json
import os
import time
from datetime import datetime

API_KEY = os.environ.get("FATHOM_API_KEY", "")
BASE_URL = "https://api.fathom.ai/external/v1"

# Filter: Only meetings after this date
CUTOFF_DATE = "2026-01-01"

# Keywords that indicate STCM140 class recordings (in title)
# These are strict matches - must have one of these in the title
TITLE_KEYWORDS = [
    "stcm140",
    "stcm 140",
    "stcm-140",
]

# Secondary title keywords - less specific but still likely class recordings
TITLE_KEYWORDS_SECONDARY = [
    "multimedia production for strategic",
]


def get_summary_text(meeting):
    """Extract summary text from meeting, handling dict/string/None."""
    summary = meeting.get("default_summary")
    if summary is None:
        return ""
    if isinstance(summary, dict):
        return summary.get("markdown_formatted", "")
    if isinstance(summary, str):
        return summary
    return ""


def fetch_all_meetings_with_transcripts():
    """Fetch all meetings from Fathom API with transcripts included."""
    headers = {"X-Api-Key": API_KEY}
    params = {
        "include_transcript": "true",
        "include_summary": "true",
        "created_after": f"{CUTOFF_DATE}T00:00:00Z",
    }

    all_meetings = []
    cursor = None

    print(f"Fetching meetings from Fathom (after {CUTOFF_DATE})...")
    print("Including transcripts and summaries (this may be slow)...\n")

    while True:
        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            f"{BASE_URL}/meetings",
            headers=headers,
            params=params
        )

        if response.status_code == 429:
            print("Rate limited, waiting 60 seconds...")
            time.sleep(60)
            continue

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        meetings = data.get("items", [])
        all_meetings.extend(meetings)

        print(f"  Fetched {len(all_meetings)} meetings so far...")

        cursor = data.get("next_cursor")
        if not cursor:
            break

    return all_meetings


def is_class_meeting(meeting):
    """Check if a meeting is a STCM140 class recording."""
    title = meeting.get("title", "").lower()

    # Check title for primary keywords (strict match)
    if any(keyword in title for keyword in TITLE_KEYWORDS):
        return True

    # Check title for secondary keywords
    if any(keyword in title for keyword in TITLE_KEYWORDS_SECONDARY):
        return True

    return False


def filter_class_meetings(meetings):
    """Filter meetings to only include STCM140 class recordings."""
    class_meetings = []

    for meeting in meetings:
        if is_class_meeting(meeting):
            class_meetings.append(meeting)

    return class_meetings


def format_transcript(transcript_data):
    """Format transcript data into readable text."""
    if not transcript_data:
        return ""

    lines = []
    for entry in transcript_data:
        # Handle speaker object
        speaker_obj = entry.get("speaker", {})
        if isinstance(speaker_obj, dict):
            speaker = speaker_obj.get("display_name", "Unknown")
        else:
            speaker = str(speaker_obj) if speaker_obj else "Unknown"

        text = entry.get("text", "")
        timestamp = entry.get("timestamp", "00:00:00")

        lines.append(f"[{timestamp}] {speaker}: {text}")

    return "\n".join(lines)


def format_date_ddmmmyy(iso_date: str) -> str:
    """Convert ISO date to DDMMMYY format (e.g., 27JAN26)."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%d%b%y").upper()
    except:
        return datetime.now().strftime("%d%b%y").upper()


def extract_clean_title(title: str) -> str:
    """Extract clean title, removing date/course prefix."""
    import re
    # Remove common prefixes like "STCM140: " or "STCM140 - "
    title = re.sub(r'^STCM\s*140\s*[:|-]\s*', '', title, flags=re.IGNORECASE)
    # Remove date suffixes like "(1/27/26)" or "(27JAN26)" or "(error, 29JAN2026)"
    title = re.sub(r'\s*\([^)]*\d+[^)]*\)\s*$', '', title)
    return title.strip()


def save_class_meeting(meeting, output_dir):
    """Save a class meeting's data to files."""
    recording_id = meeting.get("recording_id")
    title = meeting.get("title", "Untitled")
    created = meeting.get("created_at", "")
    transcript = meeting.get("transcript", [])
    summary_text = get_summary_text(meeting)
    share_url = meeting.get("share_url", "")

    # Calculate duration from recording times
    start_time = meeting.get("recording_start_time", "")
    end_time = meeting.get("recording_end_time", "")
    duration = 0
    if start_time and end_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            duration = int((end_dt - start_dt).total_seconds())
        except:
            pass

    # Format date for NotebookLM naming convention
    date_ddmmmyy = format_date_ddmmmyy(created)
    clean_title = extract_clean_title(title)

    # Parse date for display
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        date_display = dt.strftime("%B %d, %Y")
    except:
        date_display = "Unknown date"

    # NotebookLM-style filename: 🎙️ LECTURE: Title (DDMMMYY)
    notebooklm_filename = f"🎙️ LECTURE - {clean_title} ({date_ddmmmyy})"
    # Filesystem-safe version (no emoji for JSON, keep emoji for MD)
    safe_filename = f"LECTURE - {clean_title} ({date_ddmmmyy})"
    safe_filename = "".join(c if c.isalnum() or c in " -_()" else "_" for c in safe_filename)

    filename_base = safe_filename

    # Save as JSON
    json_path = os.path.join(output_dir, f"{filename_base}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meeting, f, indent=2, ensure_ascii=False)

    # Save transcript as markdown (NotebookLM format)
    md_content = f"# {clean_title}\n\n"
    md_content += f"**Type:** Class Lecture\n"
    md_content += f"**Course:** STCM140 Multimedia Production for Strategic Communications\n"
    md_content += f"**Date:** {date_display} ({date_ddmmmyy})\n"
    md_content += f"**Duration:** {duration // 60} minutes\n"
    if share_url:
        md_content += f"**Recording:** {share_url}\n"
    md_content += "\n---\n\n"

    if summary_text:
        md_content += f"## Summary\n\n{summary_text}\n\n---\n\n"

    if transcript:
        md_content += f"## Full Transcript\n\n{format_transcript(transcript)}\n"
    else:
        md_content += "*No transcript available*\n"

    # Use emoji in markdown filename for NotebookLM
    md_filename = f"🎙️ LECTURE - {clean_title} ({date_ddmmmyy}).md"
    md_filename_safe = "".join(c if c.isalnum() or c in " -_().🎙️" else "_" for c in md_filename)
    md_path = os.path.join(output_dir, md_filename_safe)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return {
        "title": title,
        "clean_title": clean_title,
        "date": date_ddmmmyy,
        "notebooklm_name": f"🎙️ LECTURE: {clean_title} ({date_ddmmmyy})",
        "recording_id": recording_id,
        "json_path": json_path,
        "md_path": md_path,
        "has_transcript": bool(transcript),
        "has_summary": bool(summary_text),
        "duration_minutes": duration // 60,
        "share_url": share_url,
    }


def main():
    # Create output directory
    output_dir = "fathom_stcm140"
    os.makedirs(output_dir, exist_ok=True)

    # Check for cached data
    cache_file = "fathom_meetings_2026.json"
    if os.path.exists(cache_file):
        print(f"Loading from cache: {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            all_meetings = json.load(f)
    else:
        # Fetch all meetings with transcripts (filtered by date in API)
        all_meetings = fetch_all_meetings_with_transcripts()

        # Save all meetings to cache
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(all_meetings, f, indent=2, ensure_ascii=False)
        print(f"All meetings saved to: {cache_file}")

    print(f"\nTotal meetings since {CUTOFF_DATE}: {len(all_meetings)}")

    # Filter for class meetings
    class_meetings = filter_class_meetings(all_meetings)
    print(f"STCM140 class meetings found: {len(class_meetings)}")

    if not class_meetings:
        print("\nNo class meetings found matching criteria.")
        print("\nRecent meeting titles for reference:")
        for m in all_meetings[:20]:
            title = m.get("title", "Untitled")
            summary = get_summary_text(m)[:100] if get_summary_text(m) else ""
            print(f"  - {title}")
            if summary:
                print(f"    Summary preview: {summary}...")
        return

    # List found meetings
    print("\nClass meetings found:")
    for i, m in enumerate(class_meetings, 1):
        title = m.get("title", "Untitled")
        created = m.get("created_at", "")[:10]
        has_transcript = "Yes" if m.get("transcript") else "No"
        has_summary = "Yes" if get_summary_text(m) else "No"
        print(f"  {i}. [{created}] {title}")
        print(f"      Transcript: {has_transcript} | Summary: {has_summary}")

    # Save each meeting
    print(f"\nSaving to: {output_dir}/")

    results = []
    for i, meeting in enumerate(class_meetings, 1):
        title = meeting.get("title", "Untitled")
        print(f"[{i}/{len(class_meetings)}] Saving: {title}")
        result = save_class_meeting(meeting, output_dir)
        if result:
            results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("EXPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Meetings exported: {len(results)}")
    print(f"With transcripts: {sum(1 for r in results if r['has_transcript'])}")
    print(f"With summaries: {sum(1 for r in results if r['has_summary'])}")
    print(f"Output directory: {output_dir}/")

    # Save index
    index_path = os.path.join(output_dir, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Index saved to: {index_path}")


if __name__ == "__main__":
    main()

"""
Fetch STCM140 class recordings from Fathom API.
"""

import requests
import json
from datetime import datetime

API_KEY = "5i3d1qz__Rep7LCiEb3EvQ.I-74TR6Elo4VijR59-5XefVhsXNYPlnCz-Mb_qqy6xU"
BASE_URL = "https://api.fathom.ai/external/v1"

def fetch_meetings(include_transcript=False):
    """Fetch all meetings from Fathom API."""
    headers = {"X-Api-Key": API_KEY}
    params = {"include_transcript": str(include_transcript).lower()}

    all_meetings = []
    cursor = None

    while True:
        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            f"{BASE_URL}/meetings",
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        meetings = data.get("items", [])
        all_meetings.extend(meetings)

        print(f"Fetched {len(meetings)} meetings (total: {len(all_meetings)})")

        cursor = data.get("next_cursor")
        if not cursor:
            break

    return all_meetings


def summarize_meetings(meetings):
    """Print a summary of available meetings."""
    print(f"\n{'='*60}")
    print(f"FATHOM MEETINGS SUMMARY")
    print(f"{'='*60}")
    print(f"Total meetings found: {len(meetings)}\n")

    for i, meeting in enumerate(meetings, 1):
        title = meeting.get("title", "Untitled")
        created = meeting.get("created_at", "Unknown date")
        duration = meeting.get("duration_seconds", 0)
        has_transcript = "transcript" in meeting and meeting["transcript"]
        has_summary = "summary" in meeting and meeting["summary"]
        share_url = meeting.get("share_url", "")

        # Parse date
        if created != "Unknown date":
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                created = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass

        # Format duration
        if duration:
            mins = duration // 60
            secs = duration % 60
            duration_str = f"{mins}m {secs}s"
        else:
            duration_str = "Unknown"

        print(f"{i}. {title}")
        print(f"   Date: {created}")
        print(f"   Duration: {duration_str}")
        print(f"   Has transcript: {has_transcript}")
        print(f"   Has summary: {has_summary}")
        if share_url:
            print(f"   Share URL: {share_url}")
        print()


if __name__ == "__main__":
    print("Fetching meetings from Fathom API...")
    print("(without transcripts first to see what's available)\n")

    meetings = fetch_meetings(include_transcript=False)

    if meetings:
        summarize_meetings(meetings)

        # Save raw response for inspection
        output_file = "fathom_meetings_raw.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(meetings, f, indent=2, ensure_ascii=False)
        print(f"\nRaw data saved to: {output_file}")
    else:
        print("No meetings found or error occurred.")

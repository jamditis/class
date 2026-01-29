"""
Fathom Webhook Server for STCM140 Class Recordings.

Receives webhooks from Fathom when recordings are processed,
filters for STCM140 classes, and uploads to Google Drive.

To run:
    python fathom_webhook_server.py

To expose publicly (for Fathom to reach):
    ngrok http 5050

Then add the ngrok URL to Fathom webhook settings.
"""

import os
import json
import hmac
import hashlib
import base64
import time
from datetime import datetime
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile

# Configuration
WEBHOOK_SECRET = "whsec_mXGGbOdhoP6Rdxj1HPDIHNxjnza1774s"
FATHOM_API_KEY = "5i3d1qz__Rep7LCiEb3EvQ.I-74TR6Elo4VijR59-5XefVhsXNYPlnCz-Mb_qqy6xU"

# Google Drive folder ID for NotebookLM sources
# Create a folder in your Drive and paste its ID here
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")

# Path to your Google service account credentials
GOOGLE_CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    r"C:\Users\Joe Amditis\.claude\gservice-credentials.json"
)

# Keywords to identify STCM140 recordings
TITLE_KEYWORDS = ["stcm140", "stcm 140", "stcm-140"]

app = Flask(__name__)


def verify_webhook_signature(payload: bytes, headers: dict) -> bool:
    """Verify Fathom webhook signature."""
    webhook_id = headers.get("webhook-id", "")
    webhook_timestamp = headers.get("webhook-timestamp", "")
    webhook_signature = headers.get("webhook-signature", "")

    if not all([webhook_id, webhook_timestamp, webhook_signature]):
        print("Missing webhook headers")
        return False

    # Check timestamp (within 5 minutes)
    try:
        timestamp = int(webhook_timestamp)
        if abs(time.time() - timestamp) > 300:
            print("Webhook timestamp too old")
            return False
    except ValueError:
        print("Invalid timestamp")
        return False

    # Create signed content
    signed_content = f"{webhook_id}.{webhook_timestamp}.{payload.decode('utf-8')}"

    # Decode secret (remove "whsec_" prefix)
    secret = WEBHOOK_SECRET
    if secret.startswith("whsec_"):
        secret = secret[6:]
    secret_bytes = base64.b64decode(secret)

    # Calculate expected signature
    expected_sig = hmac.new(
        secret_bytes,
        signed_content.encode("utf-8"),
        hashlib.sha256
    ).digest()
    expected_sig_b64 = base64.b64encode(expected_sig).decode("utf-8")

    # Compare signatures (may have version prefix like "v1,")
    for sig in webhook_signature.split(" "):
        if "," in sig:
            sig = sig.split(",")[1]
        if hmac.compare_digest(sig, expected_sig_b64):
            return True

    print("Signature mismatch")
    return False


def is_stcm140_recording(meeting_data: dict) -> bool:
    """Check if this is an STCM140 class recording."""
    title = meeting_data.get("title", "").lower()
    return any(keyword in title for keyword in TITLE_KEYWORDS)


def format_date_for_filename(iso_date: str) -> str:
    """Convert ISO date to DDMMMYY format (e.g., 27JAN26)."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%d%b%y").upper()
    except:
        return datetime.now().strftime("%d%b%y").upper()


def extract_title_for_filename(title: str) -> str:
    """Extract clean title, removing date/course prefix."""
    # Remove common prefixes like "STCM140: " or "STCM140 - "
    import re
    title = re.sub(r'^STCM\s*140\s*[:|-]\s*', '', title, flags=re.IGNORECASE)
    # Remove date suffixes like "(1/27/26)" or "(27JAN26)"
    title = re.sub(r'\s*\([^)]*\d+[^)]*\)\s*$', '', title)
    return title.strip()


def format_transcript(transcript_data: list) -> str:
    """Format transcript for NotebookLM."""
    if not transcript_data:
        return ""

    lines = []
    for entry in transcript_data:
        speaker_obj = entry.get("speaker", {})
        if isinstance(speaker_obj, dict):
            speaker = speaker_obj.get("display_name", "Unknown")
        else:
            speaker = str(speaker_obj) if speaker_obj else "Unknown"

        text = entry.get("text", "")
        timestamp = entry.get("timestamp", "00:00:00")

        lines.append(f"[{timestamp}] {speaker}: {text}")

    return "\n".join(lines)


def get_summary_text(meeting_data: dict) -> str:
    """Extract summary text from meeting data."""
    summary = meeting_data.get("default_summary") or meeting_data.get("summary")
    if summary is None:
        return ""
    if isinstance(summary, dict):
        return summary.get("markdown_formatted", "")
    if isinstance(summary, str):
        return summary
    return ""


def create_notebooklm_document(meeting_data: dict) -> tuple[str, str]:
    """
    Create a formatted document for NotebookLM.
    Returns (filename, content).
    """
    title = meeting_data.get("title", "Untitled")
    created_at = meeting_data.get("created_at", "")
    transcript = meeting_data.get("transcript", [])
    summary = get_summary_text(meeting_data)
    share_url = meeting_data.get("share_url", "")

    # Calculate duration
    start_time = meeting_data.get("recording_start_time", "")
    end_time = meeting_data.get("recording_end_time", "")
    duration_mins = 0
    if start_time and end_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            duration_mins = int((end_dt - start_dt).total_seconds() // 60)
        except:
            pass

    # Format filename with emoji and date
    date_str = format_date_for_filename(created_at)
    clean_title = extract_title_for_filename(title)
    filename = f"🎙️ LECTURE: {clean_title} ({date_str}).md"

    # Format document content
    content = f"# {clean_title}\n\n"
    content += f"**Type:** Class Lecture\n"
    content += f"**Course:** STCM140 Multimedia Production for Strategic Communications\n"
    content += f"**Date:** {date_str}\n"
    content += f"**Duration:** {duration_mins} minutes\n"
    if share_url:
        content += f"**Recording:** {share_url}\n"
    content += "\n---\n\n"

    if summary:
        content += f"## Summary\n\n{summary}\n\n---\n\n"

    if transcript:
        content += f"## Full Transcript\n\n{format_transcript(transcript)}\n"
    else:
        content += "*No transcript available*\n"

    return filename, content


def upload_to_google_drive(filename: str, content: str) -> str:
    """Upload file to Google Drive folder."""
    if not GDRIVE_FOLDER_ID:
        print("No GDRIVE_FOLDER_ID configured, skipping upload")
        return ""

    try:
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )

        # Build Drive service
        service = build("drive", "v3", credentials=credentials)

        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            temp_path = f.name

        # Upload to Drive
        file_metadata = {
            "name": filename,
            "parents": [GDRIVE_FOLDER_ID],
            "mimeType": "text/markdown",
        }
        media = MediaFileUpload(temp_path, mimetype="text/markdown")

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        # Clean up temp file
        os.unlink(temp_path)

        file_id = file.get("id")
        web_link = file.get("webViewLink", "")
        print(f"Uploaded to Drive: {filename} (ID: {file_id})")
        return web_link

    except Exception as e:
        print(f"Error uploading to Drive: {e}")
        return ""


def save_locally(filename: str, content: str) -> str:
    """Save file locally as backup."""
    output_dir = os.path.join(os.path.dirname(__file__), "fathom_stcm140")
    os.makedirs(output_dir, exist_ok=True)

    # Sanitize filename for filesystem
    safe_filename = "".join(c if c.isalnum() or c in " -_()." else "_" for c in filename)
    filepath = os.path.join(output_dir, safe_filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved locally: {filepath}")
    return filepath


@app.route("/webhook/fathom", methods=["POST"])
def handle_fathom_webhook():
    """Handle incoming Fathom webhook."""
    # Get raw payload for signature verification
    payload = request.get_data()

    # Verify signature
    if not verify_webhook_signature(payload, request.headers):
        return jsonify({"error": "Invalid signature"}), 401

    # Parse payload
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400

    print(f"\nReceived webhook: {data.get('title', 'Unknown')}")

    # Check if it's an STCM140 recording
    if not is_stcm140_recording(data):
        print("Not an STCM140 recording, skipping")
        return jsonify({"status": "skipped", "reason": "not STCM140"}), 200

    print("STCM140 recording detected! Processing...")

    # Create formatted document
    filename, content = create_notebooklm_document(data)

    # Save locally
    local_path = save_locally(filename, content)

    # Upload to Google Drive
    drive_link = upload_to_google_drive(filename, content)

    return jsonify({
        "status": "processed",
        "filename": filename,
        "local_path": local_path,
        "drive_link": drive_link,
    }), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "fathom-webhook-server"}), 200


@app.route("/", methods=["GET"])
def index():
    """Index page with status."""
    return """
    <h1>Fathom Webhook Server</h1>
    <p>STCM140 Class Recording Automation</p>
    <ul>
        <li><strong>Webhook endpoint:</strong> POST /webhook/fathom</li>
        <li><strong>Health check:</strong> GET /health</li>
    </ul>
    <p>Configure this URL in your Fathom webhook settings.</p>
    """


if __name__ == "__main__":
    print("=" * 60)
    print("FATHOM WEBHOOK SERVER FOR STCM140")
    print("=" * 60)
    print(f"Google Drive folder: {GDRIVE_FOLDER_ID or 'NOT CONFIGURED'}")
    print(f"Local output: fathom_stcm140/")
    print()
    print("Starting server on http://localhost:5050")
    print("Use ngrok to expose publicly: ngrok http 5050")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5050, debug=True)

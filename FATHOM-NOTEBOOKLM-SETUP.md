# Fathom to NotebookLM automation setup

This guide explains how to automatically sync STCM140 class recordings from Fathom to NotebookLM.

---

## Quick reference

| Component | Location |
|-----------|----------|
| Manual export script | `fathom_stcm140.py` |
| Webhook server | `fathom_webhook_server.py` |
| Output folder | `fathom_stcm140/` |
| NotebookLM | [ea55c9b0-0600-4010-a642-cc4d74833871](https://notebooklm.google.com/notebook/ea55c9b0-0600-4010-a642-cc4d74833871) |

---

## File naming convention

Files are named to match your NotebookLM organization:

| Type | Format | Example |
|------|--------|---------|
| Lecture | `🎙️ LECTURE: [title] (DDMMMYY)` | `🎙️ LECTURE: Info needs and the shiny new thing (27JAN26)` |
| Reading | `📖 READING: [title] — [source]` | `📖 READING: Is Your Journalism a Luxury or Necessity? — City Bureau` |
| Study guide | `📚 STUDY GUIDE: [title]` | `📚 STUDY GUIDE: Principles of graphic design` |

---

## Option 1: Manual export (recommended to start)

Run the export script to pull all STCM140 recordings from Fathom:

```bash
cd "C:\Users\Joe Amditis\Desktop\Crimes\playground\class"
python fathom_stcm140.py
```

This will:
1. Fetch all meetings since January 1, 2026
2. Filter for STCM140 class recordings
3. Save markdown files with transcripts and summaries to `fathom_stcm140/`

**To add to NotebookLM:**
1. Open [your NotebookLM notebook](https://notebooklm.google.com/notebook/ea55c9b0-0600-4010-a642-cc4d74833871)
2. Click "Add source" → "Upload"
3. Select the `.md` files from `fathom_stcm140/`

---

## Option 2: Automatic webhook sync

### Step 1: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start the webhook server

```bash
python fathom_webhook_server.py
```

The server will run on `http://localhost:5050`.

### Step 3: Expose with ngrok

Since Fathom needs to reach your server, use ngrok to create a public URL:

```bash
ngrok http 5050
```

Copy the `https://xxxx.ngrok.io` URL that ngrok provides.

### Step 4: Configure Fathom webhook

1. Go to [Fathom Settings → API Access](https://fathom.video/settings/api)
2. Find your API key section
3. Click "Add Webhook"
4. Enter your ngrok URL: `https://xxxx.ngrok.io/webhook/fathom`
5. Select trigger: "Recording processed" or similar
6. Save

### Step 5: Test it

Record a short test meeting with "STCM140" in the title. After processing, check:
- Terminal output from the webhook server
- `fathom_stcm140/` folder for new files

---

## Option 3: Google Drive auto-upload (advanced)

To automatically upload files to Google Drive for easier NotebookLM import:

### Step 1: Create a Google Drive folder

1. Create a folder in Google Drive for STCM140 sources
2. Copy the folder ID from the URL (the part after `/folders/`)

### Step 2: Configure the webhook server

Edit `fathom_webhook_server.py` and set:

```python
GDRIVE_FOLDER_ID = "your-folder-id-here"
```

### Step 3: Verify Google credentials

Make sure your service account has access to Drive:

```python
# Test connection
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    r"C:\Users\Joe Amditis\.claude\gservice-credentials.json",
    scopes=["https://www.googleapis.com/auth/drive.file"]
)
service = build("drive", "v3", credentials=creds)
print("Connected to Google Drive!")
```

### Step 4: Share the folder with your service account

Share the Drive folder with your service account email (found in the credentials JSON file).

---

## Troubleshooting

### No recordings found

Check that your Fathom recordings have "STCM140" in the title. The filter looks for:
- `stcm140`
- `stcm 140`
- `stcm-140`

### Webhook not receiving data

1. Verify ngrok is running and the URL is correct
2. Check Fathom webhook settings
3. Look at the terminal output from the webhook server

### Rate limiting

Fathom allows 60 API calls per minute. If you hit the limit, the script will wait 60 seconds and retry.

### Missing transcripts

Transcripts are only available after Fathom processes the recording. This usually takes 5-10 minutes after the meeting ends.

---

## API credentials reference

**Fathom API key:**
```
FATHOM_STCM140_KEY=5i3d1qz__Rep7LCiEb3EvQ.I-74TR6Elo4VijR59-5XefVhsXNYPlnCz-Mb_qqy6xU
```

**Fathom webhook secret:**
```
FATHOM_STCM140_WEBHOOK_SECRET=whsec_mXGGbOdhoP6Rdxj1HPDIHNxjnza1774s
```

---

## Files in this project

| File | Purpose |
|------|---------|
| `fathom_stcm140.py` | Manual export script - pulls recordings from Fathom API |
| `fathom_webhook_server.py` | Webhook server - receives real-time notifications |
| `fathom_meetings_2026.json` | Cache of all 2026 meetings (delete to refresh) |
| `fathom_stcm140/` | Output folder with markdown transcripts |
| `fathom_stcm140/_index.json` | Index of exported recordings |
| `requirements.txt` | Python dependencies |
| `FATHOM-NOTEBOOKLM-SETUP.md` | This guide |

---

## Resources

- [Fathom API Documentation](https://developers.fathom.ai/)
- [Fathom Webhook Documentation](https://developers.fathom.ai/webhooks)
- [NotebookLM](https://notebooklm.google.com/)
- [ngrok](https://ngrok.com/) - Free tier works fine for testing

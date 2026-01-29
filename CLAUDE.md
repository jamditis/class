# STCM140 course site

This is the GitHub Pages site and supporting tools for STCM140: Multimedia Production for Strategic Communications at Montclair State University, Spring 2026.

## Quick links

- **Live site:** https://jamditis.github.io/class/
- **GitHub repo:** https://github.com/jamditis/class
- **NotebookLM:** https://notebooklm.google.com/notebook/ea55c9b0-0600-4010-a642-cc4d74833871
- **Canvas:** https://montclair.instructure.com

## Project structure

```
class/
├── docs/                    # GitHub Pages site (Jekyll)
│   ├── _config.yml          # Jekyll config
│   ├── _layouts/
│   │   └── default.html     # Custom Tailwind layout (amditis-design-library-v2 style)
│   ├── index.md             # Home page
│   ├── schedule.md          # Week-by-week schedule
│   ├── assignments.md       # Assignment descriptions
│   ├── lectures.md          # Recordings and key concepts
│   └── resources.md         # Tools and reference materials
├── fathom_stcm140.py        # Fetch class recordings from Fathom API
├── fathom_webhook_server.py # Webhook server for auto-sync
├── fathom_fetch.py          # Basic Fathom API fetch script
├── canvas_sync.py           # Canvas LMS API integration
└── FATHOM-NOTEBOOKLM-SETUP.md  # Setup guide for Fathom → NotebookLM
```

## Environment variables

These must be set for the Python scripts to work:

```
FATHOM_API_KEY=<your-api-key>
FATHOM_WEBHOOK_SECRET=<your-webhook-secret>
```

## Course schedule (Spring 2026)

- **First class:** January 20, 2026
- **Spring Break:** March 7-15
- **Last class:** April 30, 2026
- **Final project due:** May 4, 2026
- **Schedule:** Tu/Th 10:00-11:25 AM, MRHD-143

## Assignment flow

The course follows a strategy-before-production sequence:

1. **Weeks 1-4:** Foundations (digital literacy, Cluetrain, design principles)
2. **Weeks 5-7:** Research & strategy (dossier, campaign strategy, personas)
3. **Weeks 9-13:** Production (copywriting, visuals, social graphics, branding)
4. **Weeks 14-16:** Integration (final project workshop and presentations)

## Fathom integration

Class recordings are automatically named using NotebookLM convention:
- `🎙️ LECTURE: [title] (DDMMMYY)`

Run `python fathom_stcm140.py` to fetch and export recordings to `fathom_stcm140/` folder.

## Design system

The GitHub Pages site uses a custom Jekyll layout based on the amditis-design-library-v2:

- **Fonts:** Fraunces (display), Plus Jakarta Sans (body)
- **Colors:** canvas (#ede6d4), ink (#121212), crimson (#CA3553), accent (#3d4b40)
- **Features:** Paper texture overlay, scroll-triggered nav blur, mobile drawer menu

## Common tasks

### Update the schedule

Edit `docs/schedule.md` and push to GitHub. The site rebuilds automatically.

### Add a new recording

1. Run `python fathom_stcm140.py` to fetch latest recordings
2. Add the recording link to `docs/lectures.md`
3. Commit and push

### Refresh Fathom cache

Delete `fathom_meetings_2026.json` and run the fetch script again.

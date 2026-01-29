# Canvas LMS integration guide

This guide explains how to integrate the STCM140 course materials with Canvas at Montclair State University.

---

## Quick start

### Step 1: Get your Canvas API token

1. Go to [Canvas Settings](https://montclair.instructure.com/profile/settings)
2. Scroll to **Approved Integrations**
3. Click **+ New Access Token**
4. Name it something like "STCM140 Sync"
5. Set an expiration date (optional but recommended)
6. Click **Generate Token**
7. **Copy the token immediately** — you won't see it again!

### Step 2: Find your course ID

1. Go to your STCM140 course in Canvas
2. Look at the URL: `https://montclair.instructure.com/courses/XXXXX`
3. The number after `/courses/` is your course ID

### Step 3: Set environment variables

```bash
set CANVAS_API_TOKEN=your_token_here
set CANVAS_COURSE_ID=your_course_id_here
```

Or add to your `.env` file:
```
CANVAS_API_TOKEN=your_token_here
CANVAS_COURSE_ID=your_course_id_here
```

### Step 4: Test the connection

```bash
python canvas_sync.py --list-courses
python canvas_sync.py --course-info
```

---

## Available commands

| Command | Description |
|---------|-------------|
| `--list-courses` | List all Canvas courses you have access to |
| `--list-assignments` | List all assignments in your course |
| `--list-announcements` | List recent announcements |
| `--course-info` | Get detailed course information |
| `--sync-schedule` | Preview what would be synced to Canvas |
| `--post-announcement "Title" "Message"` | Post an announcement |

---

## What you can sync

### Announcements
Post announcements directly from the command line:

```bash
python canvas_sync.py --post-announcement "Class update" "Remember, the slide deck assignment is due Thursday!"
```

### Assignments
The script can create and update assignments with:
- Name and description
- Due dates
- Point values
- Submission types

### Calendar events
Sync the course schedule to the Canvas calendar.

---

## API endpoints reference

| Endpoint | Use |
|----------|-----|
| `/api/v1/courses` | List courses |
| `/api/v1/courses/:id/assignments` | Manage assignments |
| `/api/v1/courses/:id/discussion_topics` | Announcements |
| `/api/v1/announcements` | List announcements |
| `/api/v1/courses/:id/modules` | Course modules |
| `/api/v1/courses/:id/pages` | Course pages |

Full documentation: [Canvas LMS REST API](https://canvas.instructure.com/doc/api/)

---

## Automation ideas

### 1. Auto-post lecture recordings
After each class, automatically post an announcement with the Fathom recording link:

```python
# Example integration with Fathom webhook
def on_new_recording(recording):
    if is_stcm140_recording(recording):
        title = f"Recording: {recording['title']}"
        message = f"Class recording is now available: {recording['share_url']}"
        post_announcement(title, message)
```

### 2. Sync GitHub Pages to Canvas
Keep the Canvas syllabus page updated from the GitHub Pages site.

### 3. Assignment reminders
Automatically post reminders 3 days before assignments are due.

### 4. Grade notifications
Post summary announcements after grading batches of assignments.

---

## Security notes

- **Never commit your API token to git**
- Use environment variables or a `.env` file
- The `.gitignore` already excludes `.env` files
- Tokens can be revoked in Canvas Settings if compromised
- Set reasonable expiration dates on tokens

---

## Troubleshooting

### "401 Unauthorized"
Your token is invalid or expired. Generate a new one in Canvas Settings.

### "403 Forbidden"
You don't have permission for that action. Check that you're the instructor for the course.

### "404 Not Found"
The course ID is wrong, or the resource doesn't exist.

### Rate limiting
Canvas limits API requests. If you hit the limit, wait a few minutes before trying again.

---

## Resources

- [Canvas LMS REST API Documentation](https://canvas.instructure.com/doc/api/)
- [Canvas Developer Documentation Portal](https://developerdocs.instructure.com/)
- [Montclair Canvas Login](https://montclair.instructure.com/)

# ReelForge MVP

Convert any website URL into a 1080×1920 marketing reel — locally, no cloud needed.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| FFmpeg | Any recent | https://ffmpeg.org/download.html |

> FFmpeg must be in your system PATH.

---

## Quick Setup

```powershell
# Run once
.\setup.ps1
```

Or manually:

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium

# Frontend
cd ..\frontend
npm install
```

---

## Running

Open **two terminals**:

**Terminal 1 — Backend**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Usage

1. Paste any public URL (e.g. `https://stripe.com`)
2. Click **Generate Video**
3. Wait ~30–60 seconds (Playwright + FFmpeg)
4. Preview the vertical reel and click **Download**

---

## Project Structure

```
REELFROGE/
├── backend/
│   ├── main.py              # FastAPI app (Playwright + FFmpeg logic)
│   ├── requirements.txt
│   ├── screenshots/         # Temp — auto-cleaned after each run
│   ├── output/              # Generated MP4 files
│   └── assets/
│       └── music.mp3        # Optional background music (drop here)
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Single-page UI
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.ts       # Proxies /generate → localhost:8000
│   └── package.json
├── setup.ps1                # One-click setup script
└── README.md
```

---

## API

### `POST /generate`
```json
// Request
{ "url": "https://stripe.com" }

// Response
{
  "status": "success",
  "video": "output/<session_id>.mp4",
  "session_id": "<uuid>"
}
```

### `GET /output/<filename>`
Streams the MP4 file.

---

## Screenshot Strategy

| # | Position |
|---|----------|
| 0 | Hero (0%) |
| 1 | 20% scroll |
| 2 | 40% scroll |
| 3 | 60% scroll |
| 4 | 80% scroll |
| 5 | Bottom (100%) |

---

## Video Specs

- **Resolution:** 1080×1920 (vertical / 9:16)
- **Duration:** 12 seconds
- **Each frame:** 2 seconds with slow zoom-in/out
- **Transitions:** Smooth fade in/out per slide
- **Codec:** H.264 (libx264), AAC audio (if music present)

---

## Optional Background Music

Drop any MP3 file at:
```
backend/assets/music.mp3
```
It will be automatically mixed into the video output.

---

## Error Handling

| Error | Message shown |
|-------|--------------|
| Invalid URL | "Invalid URL provided." |
| Website timeout | Screenshot capture failed (30s timeout) |
| Screenshot failure | Detailed message from Playwright |
| FFmpeg failure | Last 500 chars of FFmpeg stderr |

# Converter App

**A small Windows desktop tool I built to stop doing boring file conversions by hand, plus an automatic text-to-audiobook watcher.**

Built with Python and AI-assisted development.

---

## What it does

One window, five buttons:

| Button | What happens |
|---|---|
| **Image(s) → PDF** | Pick several images and they're merged into one PDF, in filename order |
| **MP4 → MP3** | Pulls the audio out of a video (ffmpeg, no console popup) |
| **PDF → Word** | Full layout conversion with `pdf2docx`. Falls back to text-only if that library isn't installed. |
| **Word → PDF** | Converts `.docx` to PDF (uses Microsoft Word) |
| **Text → MP3 watcher** | Starts the audiobook watcher in its own window (see below) |

Conversions run in a **background thread**, so the window doesn't freeze while it works.

---

## Text → MP3 watcher (`watcher.py`)

I read long web novels, so I automated turning chapters into audio:

1. Paste a chapter into `story.txt` and press **Ctrl+S**
2. The watcher notices the save and turns it into an MP3 named after the chapter (e.g. `Chapter 0131.mp3`)
3. Done. Paste the next chapter.

**The details that make it reliable:**
- **Save detection with a settle delay:** waits until the file stops changing, so it never reads a half-saved file
- **No duplicates:** hashes the text and skips saves with no real change
- **Smart chunking:** splits long text at paragraph and sentence ends, so the voice never cuts off mid-sentence
- **Skipped-text check:** compares the words actually spoken against the text. If less than 97% was read, that piece is retried (up to 4 times).
- **Safe writes:** builds the MP3 as a `.part` file and only renames it when fully finished, so you never open a broken file
- **Auto cleanup:** keeps only the newest 20 chapters
- **One-word voice switch:** set `ACTIVE = "male"` or `"female"` and tune rate and pitch

### Voice testing tools (`Test Subfolders/`)
- `voice_samples.py` generates the same sentence in every English voice, plus a key file listing each voice's style, to pick a voice by ear
- `ryan_samples.py` generates a grid of pitch × speed combinations for one voice
- `tts.py` is the first simple version: paste text, get one MP3

---

## Tech stack
Python, Tkinter, threading, asyncio, `edge-tts`, ffmpeg (`imageio-ffmpeg`), Pillow, `pdf2docx` / `pypdf` + `python-docx`, `docx2pdf`

## Run it
```bash
pip install edge-tts imageio-ffmpeg pillow pdf2docx pypdf python-docx docx2pdf
python "Converter App/converter_app.py"
```

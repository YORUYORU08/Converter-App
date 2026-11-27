import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog

APP_DIR = os.path.dirname(os.path.abspath(__file__))
NO_WINDOW = 0x08000000 if os.name == "nt" else 0   # hides the ffmpeg console popup


# ---------- converters ----------

def images_to_pdf(paths, out):
    from PIL import Image
    imgs = [Image.open(p).convert("RGB") for p in sorted(paths)]  # sorted by filename
    imgs[0].save(out, save_all=True, append_images=imgs[1:])
    return out


def mp4_to_mp3(path):
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out = os.path.splitext(path)[0] + ".mp3"
    r = subprocess.run(
        [ffmpeg, "-y", "-i", path, "-vn", "-codec:a", "libmp3lame", "-q:a", "2", out],
        capture_output=True, text=True, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-300:])
    return out


def pdf_to_word(path):
    out = os.path.splitext(path)[0] + ".docx"
    try:
        from pdf2docx import Converter          # full layout, if installed
        cv = Converter(path)
        cv.convert(out)
        cv.close()
        return f"{out} (full layout)"
    except ImportError:
        from pypdf import PdfReader             # lightweight text-only fallback
        from docx import Document
        doc = Document()
        for page in PdfReader(path).pages:
            doc.add_paragraph(page.extract_text() or "")
        doc.save(out)
        return f"{out} (text only)"


def word_to_pdf(path):
    from docx2pdf import convert                # needs Microsoft Word installed
    out = os.path.splitext(path)[0] + ".pdf"
    convert(path, out)
    return out


# ---------- GUI plumbing ----------

root = tk.Tk()
root.title("Converter App")
root.geometry("460x420")
status = tk.StringVar(value="Pick a converter.")


def run_in_background(fn, *args):
    def worker():
        try:
            result = fn(*args)
            msg = f"Done: {result}"
        except Exception as e:
            msg = f"Error: {e}"
        root.after(0, lambda: status.set(msg))
    status.set("Working... (the window may lag a bit, that's normal)")
    threading.Thread(target=worker, daemon=True).start()


def pick(title, patterns, multiple=False):
    f = filedialog.askopenfilenames if multiple else filedialog.askopenfilename
    return f(title=title, filetypes=patterns)


def do_images():
    paths = pick("Choose images", [("Images", "*.jpg *.jpeg *.png *.bmp *.webp")], True)
    if not paths:
        return
    out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                       initialfile="images.pdf")
    if out:
        run_in_background(images_to_pdf, paths, out)


def do_mp4():
    p = pick("Choose a video", [("Video", "*.mp4 *.mkv *.mov *.avi *.webm")])
    if p:
        run_in_background(mp4_to_mp3, p)


def do_pdf2word():
    p = pick("Choose a PDF", [("PDF", "*.pdf")])
    if p:
        run_in_background(pdf_to_word, p)


def do_word2pdf():
    p = pick("Choose a Word file", [("Word", "*.docx *.doc")])
    if p:
        run_in_background(word_to_pdf, p)


def start_tts_watcher():
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    subprocess.Popen([sys.executable, "watcher.py"], cwd=APP_DIR, creationflags=flags)
    status.set("Text to MP3 watcher started in its own window.")


tk.Label(root, text="Converter App", font=("Segoe UI", 16, "bold")).pack(pady=12)
for label, cmd in [
    ("Image(s)  →  PDF", do_images),
    ("MP4  →  MP3", do_mp4),
    ("PDF  →  Word", do_pdf2word),
    ("Word  →  PDF", do_word2pdf),
    ("Start Text → MP3 watcher (Ryan)", start_tts_watcher),
]:
    tk.Button(root, text=label, command=cmd, width=34, height=2).pack(pady=4)

tk.Label(root, textvariable=status, wraplength=420, fg="#444").pack(pady=14)
root.mainloop()
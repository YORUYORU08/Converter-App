import asyncio
import hashlib
import os
import re
import time
import edge_tts

# ============================================================
#  VOICE SWITCH  ->  change this one word to pick the voice
# ============================================================
ACTIVE = "male"            # "male" or "female"

MALE = {
    "voice": "en-GB-RyanNeural",
    "rate":  "+75%",       # 2x of your preferred -15% speed. Use "+100%" for 2x of normal Ryan
    "pitch": "-15Hz",
}

FEMALE = {
    "voice": "en-CA-ClaraNeural",   # swap in whichever voice you liked from voice_samples.py
    "rate":  "+0%",       # same speed as Ryan; lower it if she sounds rushed
    "pitch": "+0Hz",       # a lowered pitch tends to sound odd on female voices; leave at +0Hz to start
}
# ============================================================

if ACTIVE.lower() not in ("male", "female"):
    raise SystemExit(f'ACTIVE must be "male" or "female", not "{ACTIVE}"')
_v = MALE if ACTIVE.lower() == "male" else FEMALE
VOICE, RATE, PITCH = _v["voice"], _v["rate"], _v["pitch"]

INPUT_FILE = "story.txt"   # the file you paste into and save
OUT_DIR = "mp3s"           # finished MP3s go here
PAD = 4                    # Chapter 0005 sorts correctly; use 3 for Chapter 005, 1 for no padding
KEEP = 20                  # how many of the newest chapters to keep
CHECK_EVERY = 1            # seconds between checks
SETTLE = 1.5               # wait this long after a save, in case it's still writing

CHUNK_CHARS = 800          # size of each piece sent to the voice (smaller = safer)
RETRIES = 4                # attempts per piece before giving up
MIN_MATCH = 0.97           # how much of the text must be spoken to count as "complete"


def make_name(text: str) -> str:
    """Build the MP3 name from the first line, e.g. 'Chapter 100: Revelation' -> 'Chapter 0100'."""
    first_line = text.strip().splitlines()[0]
    m = re.match(r"\s*chapter\s*(\d+)", first_line, re.IGNORECASE)
    if m:
        return f"Chapter {int(m.group(1)):0{PAD}d}"
    return time.strftime("Untitled %Y-%m-%d %H-%M-%S")


def file_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def read_text() -> str:
    with open(INPUT_FILE, encoding="utf-8") as f:
        return f.read()


def cleanup_old():
    """Keep only the newest KEEP chapters (by chapter number). Deletes permanently."""
    chapters = []
    for fname in os.listdir(OUT_DIR):
        m = re.fullmatch(r"Chapter (\d+)\.mp3", fname, re.IGNORECASE)
        if m:
            chapters.append((int(m.group(1)), fname))

    if len(chapters) <= KEEP:
        return

    chapters.sort()                      # lowest chapter number first
    for num, fname in chapters[:-KEEP]:  # everything except the newest KEEP
        try:
            os.remove(os.path.join(OUT_DIR, fname))   # permanent, no Recycle Bin
            print(f"    Deleted old chapter: {fname}")
        except Exception as e:
            print(f"    Could not delete {fname}: {e}")


def split_text(text: str):
    """Split into chunks at paragraph/sentence ends, each <= CHUNK_CHARS."""
    pieces = []
    for para in re.split(r"\n\s*\n|\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= CHUNK_CHARS:
            pieces.append(para)
        else:
            pieces.extend(s for s in re.split(r"(?<=[.!?…\"”])\s+", para) if s.strip())

    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + len(p) + 1 > CHUNK_CHARS:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur}\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def alnum_len(s: str) -> int:
    return len(re.sub(r"[\W_]+", "", s))


async def speak_chunk(chunk: str, label: str) -> bytes:
    """Generate one chunk, verify nothing was skipped, retry if it was."""
    best = b""
    for attempt in range(1, RETRIES + 1):
        try:
            try:
                comm = edge_tts.Communicate(chunk, VOICE, rate=RATE, pitch=PITCH,
                                            boundary="WordBoundary")
            except TypeError:                      # older edge-tts without that option
                comm = edge_tts.Communicate(chunk, VOICE, rate=RATE, pitch=PITCH)

            audio, spoken = bytearray(), []
            async for m in comm.stream():
                if m["type"] == "audio":
                    audio += m["data"]
                elif m["type"] in ("WordBoundary", "SentenceBoundary"):
                    spoken.append(m["text"])

            if len(audio) > len(best):
                best = bytes(audio)

            if not audio:
                raise RuntimeError("no audio received")

            if spoken:                             # can verify
                ratio = alnum_len("".join(spoken)) / max(1, alnum_len(chunk))
                if ratio < MIN_MATCH:
                    raise RuntimeError(f"only {ratio:.0%} of the text was spoken")
            return bytes(audio)
        except Exception as e:
            print(f"    {label}: attempt {attempt}/{RETRIES} failed ({e})")
            await asyncio.sleep(2)

    print(f"    WARNING: {label} may have a skipped part. Check it.")
    return best


async def build_mp3(text: str, path: str):
    chunks = split_text(text)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        for i, chunk in enumerate(chunks, 1):
            print(f"    part {i}/{len(chunks)}", end="\r")
            f.write(await speak_chunk(chunk, f"part {i}"))
    os.replace(tmp, path)                          # only appears when fully finished
    print(" " * 30, end="\r")


def generate(text: str):
    name = make_name(text)
    path = os.path.join(OUT_DIR, f"{name}.mp3")
    print(f"[{time.strftime('%H:%M:%S')}] Generating {name}.mp3 ({VOICE}) ...")
    start = time.time()
    asyncio.run(build_mp3(text, path))
    print(f"    Done in {time.time() - start:.0f}s -> {path}")
    cleanup_old()
    print()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cleanup_old()                        # also clean up when the script starts
    if not os.path.exists(INPUT_FILE):
        open(INPUT_FILE, "w", encoding="utf-8").close()

    last_mtime = os.path.getmtime(INPUT_FILE)
    last_hash = file_hash(read_text())

    print(f"Active voice: {ACTIVE.upper()}  ->  {VOICE}  (rate {RATE}, pitch {PITCH})")
    print(f"Watching '{INPUT_FILE}'. Paste a chapter, save (Ctrl+S), and the MP3 is made.")
    print("First line should look like: Chapter 100: Revelation")
    print(f"Keeping the newest {KEEP} chapters. Press Ctrl+C to stop.\n")

    while True:
        try:
            time.sleep(CHECK_EVERY)
            mtime = os.path.getmtime(INPUT_FILE)
            if mtime == last_mtime:
                continue

            # wait until the file stops changing
            while True:
                time.sleep(SETTLE)
                new_mtime = os.path.getmtime(INPUT_FILE)
                if new_mtime == mtime:
                    break
                mtime = new_mtime
            last_mtime = mtime

            text = read_text().strip()
            if not text:
                continue
            h = file_hash(text)
            if h == last_hash:        # saved again with no real changes
                continue
            last_hash = h

            generate(text)
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()